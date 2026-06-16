"""
One-time data migration: Excel → SQLite.
Run: python -m data.migrate_data
"""
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

# Add parent to path for bridge_db import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bridge_db import init_bridge_db, execute, executemany

# Source directories — prioritize local source/, fallback to Files/
_SELF_DIR = Path(__file__).resolve().parent
FACILITY_DIR = _SELF_DIR / "source"
if not FACILITY_DIR.exists():
    FACILITY_DIR = Path(__file__).resolve().parent.parent.parent / "Files" / "effect" / "facility_parameters"
TABLE_DIR = FACILITY_DIR / "table"
BRIDGE_DATA_DIR = FACILITY_DIR / "bridge_data"

def _find_excel(filename: str) -> Path:
    """Find an Excel file: try FACILITY_DIR directly first, then TABLE_DIR."""
    path = FACILITY_DIR / filename
    if path.exists():
        return path
    return TABLE_DIR / filename

# Highway name mapping (from domain knowledge)
HIGHWAY_NAMES = {
    "G15":   "沈海高速",
    "G76":   "厦蓉高速",
    "G25":   "长深高速",
    "G70":   "福银高速",
    "G3":    "京台高速",
    "G1505": "福州绕城高速",
    "G1517": "莆炎高速",
    "G1523": "甬莞高速",
    "G7021": "宁光高速",
    "S53":   "渔平支线",
    "S11":   "福厦高速",
}


def migrate_highways():
    """Migrate highway codes and names."""
    print("[migrate] highways...")
    df = pd.read_excel(str(_find_excel("highways.xlsx"))
    rows = 0
    for _, row in df.iterrows():
        code = str(row.iloc[0]).strip()
        if code and code != "nan":
            name = HIGHWAY_NAMES.get(code, code)
            category = "G" if code.startswith("G") else "S"
            execute(
                "INSERT OR IGNORE INTO highways (highway_code, highway_name, category) VALUES (?, ?, ?)",
                (code, name, category)
            )
            rows += 1
    print(f"  {rows} highways inserted")


def migrate_junctions():
    """Migrate junction names and GPS coordinates."""
    print("[migrate] junctions...")
    df = pd.read_excel(str(_find_excel("junctions.xlsx"))
    rows = 0
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        # Clean \r suffix from column 1 (junction_type)
        jtype_raw = str(row.iloc[1]) if pd.notna(row.iloc[1]) else "普通"
        jtype = jtype_raw.replace("_x000d_", "").strip()
        loc = str(row.iloc[2]).strip()
        parts = loc.split(",")
        if len(parts) >= 2:
            lon, lat = float(parts[0]), float(parts[1])
            execute(
                "INSERT OR IGNORE INTO junctions (junction_name, junction_type, longitude, latitude) VALUES (?, ?, ?, ?)",
                (name, jtype, lon, lat)
            )
            rows += 1
    print(f"  {rows} junctions inserted")


def migrate_junction_positions():
    """Migrate junction positions (K values on highways)."""
    print("[migrate] junction_positions...")
    df = pd.read_excel(str(_find_excel("junctions_positions.xlsx"))
    rows = 0
    for _, row in df.iterrows():
        name = str(row.iloc[1]).strip()
        code = str(row.iloc[2]).strip()
        k_val = float(row.iloc[3])
        k_str_raw = str(row.iloc[4]) if pd.notna(row.iloc[4]) else f"k{int(k_val)}"
        k_str = k_str_raw.replace("_x000d_", "").strip()
        try:
            execute(
                "INSERT OR IGNORE INTO junction_positions (junction_name, highway_code, k_value, k_string) VALUES (?, ?, ?, ?)",
                (name, code, k_val, k_str)
            )
            rows += 1
        except Exception as e:
            print(f"  WARN: skip {name}/{code}: {e}")
    print(f"  {rows} junction_positions inserted")


def build_road_sections():
    """Build road_sections by connecting adjacent junctions on same highway."""
    print("[migrate] building road_sections...")
    from app.bridge_db import query

    # Get all junction positions grouped by highway
    positions = query("""
        SELECT junction_name, highway_code, k_value
        FROM junction_positions
        ORDER BY highway_code, k_value
    """)

    # Group by highway
    by_highway = {}
    for p in positions:
        hw = p["highway_code"]
        if hw not in by_highway:
            by_highway[hw] = []
        by_highway[hw].append((p["junction_name"], p["k_value"]))

    rows = 0
    for hw, pos_list in by_highway.items():
        pos_list.sort(key=lambda x: x[1])  # sort by K value
        for i in range(len(pos_list) - 1):
            j_from, k_from = pos_list[i]
            j_to, k_to = pos_list[i + 1]
            # Don't create self-loops
            if j_from == j_to:
                continue
            execute(
                """INSERT OR IGNORE INTO road_sections
                   (junction_from, junction_to, highway_code, k_from, k_to, direction)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (j_from, j_to, hw, k_from, k_to)
            )
            rows += 1
    print(f"  {rows} road_sections built")


def migrate_bridges():
    """Migrate bridge inventory from Excel."""
    print("[migrate] bridges...")
    df = pd.read_excel(str(_find_excel("bridge_list.xlsx"))

    column_map = {
        "桩号": "station",
        "桥型": "bridge_type",
        "跨径": "span",
        "梁片数": "beam_count",
        "车道数": "lane_count",
        "大件车行驶车道": "heavy_lane",
        "控制截面": "control_section",
        "公路等级": "road_class",
        "结构基频": "frequency",
        "正弯矩（midas计算）": "pos_moment_midas",
        "负弯矩（midas计算）": "neg_moment_midas",
        "剪力（midas计算）": "shear_midas",
        "正弯矩设计值": "pos_moment_design",
        "负弯矩设计值": "neg_moment_design",
        "剪力设计值": "shear_design",
        "所属高速": "highway_code",
    }

    rows = 0
    for _, row in df.iterrows():
        vals = {}
        for cn_col, en_col in column_map.items():
            val = row[cn_col]
            if pd.isna(val):
                vals[en_col] = None
            elif isinstance(val, float):
                vals[en_col] = val
            else:
                vals[en_col] = str(val).strip()

        # Normalize station to lowercase
        station = vals.get("station", "")
        if station:
            station = station.lower()
            vals["station"] = station

        # Determine data folder name (try both cases)
        data_folder = None
        if station:
            # Try exact match first
            candidates = [
                station.upper(),  # K0+15
                station,          # k0+15
                station.replace("k", "K"),  # K0+15
            ]
            existing = set(
                d.name for d in BRIDGE_DATA_DIR.iterdir()
                if d.is_dir()
            ) if BRIDGE_DATA_DIR.exists() else set()
            for c in candidates:
                if c in existing:
                    data_folder = c
                    break
            if not data_folder:
                # Try case-insensitive
                for d_name in existing:
                    if d_name.lower() == station.lower():
                        data_folder = d_name
                        break

        vals["data_folder"] = data_folder

        hw_code = vals.get("highway_code")
        if hw_code and hw_code.lower() in ("nan", "none", ""):
            hw_code = None

        try:
            execute(
                """INSERT INTO bridges
                   (station, bridge_type, span, beam_count, lane_count, heavy_lane,
                    control_section, road_class, frequency,
                    pos_moment_midas, neg_moment_midas, shear_midas,
                    pos_moment_design, neg_moment_design, shear_design,
                    highway_code, data_folder)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    vals.get("station"),
                    vals.get("bridge_type"),
                    vals.get("span"),
                    vals.get("beam_count"),
                    vals.get("lane_count"),
                    vals.get("heavy_lane"),
                    vals.get("control_section"),
                    vals.get("road_class"),
                    vals.get("frequency"),
                    vals.get("pos_moment_midas"),
                    vals.get("neg_moment_midas"),
                    vals.get("shear_midas"),
                    vals.get("pos_moment_design"),
                    vals.get("neg_moment_design"),
                    vals.get("shear_design"),
                    hw_code,
                    vals.get("data_folder"),
                )
            )
            rows += 1
        except Exception as e:
            print(f"  WARN: skip bridge {station}: {e}")

    print(f"  {rows} bridges inserted")


def parse_influence_line_file(filepath: str) -> list[dict]:
    """Parse a MIDAS influence line TXT file."""
    results = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Skip header lines (first ~6 lines are metadata)
    data_start = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # Data lines look like: "    1      0.000      0.000   -6.936329e-07"
        parts = line.split()
        if len(parts) >= 4:
            try:
                float(parts[0])  # element number
                float(parts[1])  # position
                float(parts[2])  # distance
                float(parts[3])  # influence value
                data_start = i
                break
            except ValueError:
                continue

    for line in lines[data_start:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 4:
            try:
                elem = int(parts[0])
                pos = float(parts[1])
                dist = float(parts[2])
                inf_val = float(parts[3])
                results.append({
                    "elem": elem,
                    "position": pos,
                    "distance": dist,
                    "influence_val": inf_val,
                })
            except (ValueError, IndexError):
                continue

    return results


def migrate_influence_lines():
    """Migrate MIDAS influence line data from TXT files."""
    print("[migrate] influence lines...")

    from app.bridge_db import query

    bridges = query("SELECT id, station, data_folder FROM bridges WHERE data_folder IS NOT NULL")
    print(f"  Found {len(bridges)} bridges with data folders")

    if not BRIDGE_DATA_DIR.exists():
        print(f"  WARN: Bridge data dir not found: {BRIDGE_DATA_DIR}")
        return

    total_lines = 0
    skipped = 0

    for bridge in bridges:
        folder = BRIDGE_DATA_DIR / bridge["data_folder"]
        if not folder.exists():
            skipped += 1
            continue

        # Find the 3 influence line files
        txt_files = list(folder.glob("*.txt"))
        if not txt_files:
            skipped += 1
            continue

        bridge_id = bridge["id"]

        for tf in txt_files:
            fname = tf.name
            if "正弯矩" in fname:
                line_type = "pos_moment"
            elif "负弯矩" in fname:
                line_type = "neg_moment"
            elif "剪力" in fname:
                line_type = "shear"
            else:
                continue

            try:
                rows = parse_influence_line_file(str(tf))
                if not rows:
                    continue

                # Batch insert
                params_list = [
                    (bridge_id, line_type, r["elem"], r["position"], r["distance"], r["influence_val"])
                    for r in rows
                ]

                # Insert in chunks to avoid memory issues
                chunk_size = 5000
                for i in range(0, len(params_list), chunk_size):
                    chunk = params_list[i:i + chunk_size]
                    executemany(
                        """INSERT INTO bridge_influence_lines
                           (bridge_id, line_type, elem, position, distance, influence_val)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        chunk
                    )
                    total_lines += len(chunk)
            except Exception as e:
                print(f"  WARN: {fname}: {e}")

    print(f"  {total_lines} influence line rows inserted")
    if skipped:
        print(f"  {skipped} bridges skipped (no data folder or files)")


def main():
    print("=" * 50)
    print("CargoNavigator Data Migration")
    print("=" * 50)

    # Initialize database
    init_bridge_db()

    # Run migrations in order
    migrate_highways()
    migrate_junctions()
    migrate_junction_positions()
    build_road_sections()
    migrate_bridges()
    migrate_influence_lines()

    # Summary
    from app.bridge_db import query
    tables = ["highways", "junctions", "junction_positions", "road_sections", "bridges", "bridge_influence_lines"]
    print("\n" + "=" * 50)
    print("Migration Summary:")
    for t in tables:
        result = query(f"SELECT COUNT(*) as cnt FROM {t}")
        cnt = result[0]["cnt"] if result else 0
        print(f"  {t}: {cnt} rows")
    print("=" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
