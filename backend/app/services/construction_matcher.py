"""
Construction Event K-Value Matcher.

Parses Spider Markdown files to extract structured construction/traffic events,
then matches them to route segments by highway code + K-value range overlap.

Key insight: Spider filenames already contain date, highway name, and K-values.
    Format: {date}_{time}_{highway_name}_K{start}_{K{end}}.md
"""
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from app.bridge_db import query, query_one

logger = logging.getLogger(__name__)

# Highway name → code mapping (Chinese name → G/S code)
HIGHWAY_NAME_MAP = {
    # National highways (G-series) - primary
    "沈海高速": "G15",
    "厦蓉高速": "G76",
    "长深高速": "G25",
    "福银高速": "G70",
    "京台高速": "G3",
    "福州绕城高速": "G1505",
    "莆炎高速": "G1517",
    "甬莞高速": "G1523",
    "宁光高速": "G7021",
    # National highways (G-series) - regional/branch
    "泉南高速": "G72",
    "宁上高速": "G1514",
    "宁武高速": "G1514",    # 宁武=宁德-武夷山, part of G1514
    "沙厦高速": "G2517",
    # Provincial highways (S-series)
    "渔平支线": "S53",
    "渔平高速": "S53",
    "福厦高速": "S11",
    "永漳高速": "S30",
    "漳武高速": "S40",
    "沙南高速": "S22",
    "浦武高速": "S0311",
    "政永高速": "S21",
    "秀永高速": "S55",
    "云平高速": "S62",
    # Branch/support lines
    "东山支线": "S64",
    "上杭支线高速": "S66",
    "平和支线": "S63",
    # Historical/alias names
    "泉厦高速": "G15",     # 泉州-厦门段 = 沈海高速一部分
    "漳龙高速": "G76",     # 漳州-龙岩段 = 厦蓉高速一部分
    "漳诏高速": "G15",     # 漳州-诏安段
    "福宁高速": "G15",     # 福州-宁德段
    "罗宁高速": "G15",     # 罗源-宁德段
    "厦漳高速": "G15",     # 厦门-漳州段
    "龙长高速": "G76",     # 龙岩-长汀段
    "永宁高速": "G72",     # 永安-宁化段 (part of G72)
    "浦南高速": "G3",      # 浦城-南平段
    "三福高速": "G70",     # 三明-福州段
    "邵三高速": "G70",     # 邵武-三明段
    "福州机场高速": "S1531",
}

# Spider data directory
SPIDER_DATA = Path(__file__).resolve().parent.parent.parent / "spider" / "data" / "road_details"


@dataclass
class ConstructionEvent:
    """A single construction/traffic event."""
    filename: str
    highway_name: str      # Chinese name, e.g. "沈海高速"
    highway_code: str       # G/S code, e.g. "G15"
    k_start: float          # K value start (km)
    k_end: float            # K value end (km)
    direction: str          # "A道", "B道", "未知方向"
    event_time: str         # e.g. "2026-03-14 12:17:13"
    description: str        # Brief description
    url: str                # Source URL


def parse_k_value(k_str: str) -> Optional[float]:
    """Parse a K-value string to float (km).

    Examples:
        "K2338" → 2338.0
        "K28+600" → 28.6
        "K1946+500" → 1946.5
        "K2410" → 2410.0
    """
    k_str = k_str.strip().upper().replace(" ", "")
    # Pattern: K<major>[+<minor>]
    m = re.match(r'K(\d+)(?:\+(\d+))?', k_str)
    if m:
        major = float(m.group(1))
        minor = float(m.group(2)) / 1000.0 if m.group(2) else 0.0
        return major + minor
    return None


def parse_filename_k_values(filename: str) -> Optional[tuple[str, float, float]]:
    """Extract highway name and K-range from filename.

    Examples:
        "2026-03-14_12-17-13_厦蓉高速_K28_600_K28_850.md"
        → ("厦蓉高速", 28.6, 28.85)
        "2022-07-15_08-00-46_沈海高速_K2338_K2344.md"
        → ("沈海高速", 2338.0, 2344.0)
    """
    # Strip extension
    name = filename.rsplit(".", 1)[0]

    # Pattern: {YYYY-MM-DD}_{HH-MM-SS}_{highway_name}_K{start}_K{end}
    m = re.match(
        r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_(.+?)_K(\d+(?:_\d+)?)_K(\d+(?:_\d+)?)$',
        name
    )
    if not m:
        # Try flexible fallback: anything_before_Kstart_Kend
        m = re.match(r'(.+?)_K(\d+(?:_\d+)?)_K(\d+(?:_\d+)?)$', name)
        if m:
            # The captured group includes date_time_, strip it
            raw_name = m.group(1)
            # Remove date and time prefix: YYYY-MM-DD_HH-MM-SS_
            cleaned = re.sub(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_', '', raw_name)
            if cleaned:
                return cleaned, parse_k_value("K" + m.group(2).replace("_", "+")), parse_k_value("K" + m.group(3).replace("_", "+"))
        return None

    hw_name = m.group(1)
    k_start_str = m.group(2).replace("_", "+")
    k_end_str = m.group(3).replace("_", "+")

    k_start = parse_k_value("K" + k_start_str)
    k_end = parse_k_value("K" + k_end_str)

    if k_start is None or k_end is None:
        return None

    return hw_name, k_start, k_end


def parse_markdown_content(content: str) -> dict:
    """Extract structured fields from Markdown content."""
    result = {
        "direction": "未知方向",
        "event_time": "",
        "description": "",
        "url": "",
    }

    # Extract URL
    m = re.search(r'\*\*URL\*\*:\s*(.+?)(?:\n|$)', content)
    if m:
        result["url"] = m.group(1).strip()

    # Extract event time
    m = re.search(r'\*\*发布时间\*\*:\s*(.+?)(?:\n|$)', content)
    if m:
        result["event_time"] = m.group(1).strip()

    # Extract direction
    m = re.search(r'##\s*方向\s*\n+(.+?)(?:\n|$)', content)
    if m:
        result["direction"] = m.group(1).strip()

    # Extract桩号区间 (from content, used as validation)
    m = re.search(r'##\s*桩号区间\s*\n+(.+?)(?:\n|$)', content)
    if m:
        result["station_range"] = m.group(1).strip()

    # Extract description
    m = re.search(r'##\s*更新简介\s*\n+(.+?)(?:\n|$)', content)
    if m:
        result["description"] = m.group(1).strip()

    return result


def load_all_events(data_dir: Optional[Path] = None) -> list[ConstructionEvent]:
    """Load and parse all Spider construction events into structured objects."""
    if data_dir is None:
        data_dir = SPIDER_DATA

    events = []

    # Construction events
    construction_dir = data_dir / "road_construction_details"
    if construction_dir.exists():
        for fp in construction_dir.glob("*.md"):
            try:
                evt = _parse_single_event(fp)
                if evt:
                    events.append(evt)
            except Exception as e:
                logger.warning(f"Failed to parse {fp.name}: {e}")

    # Traffic incidents
    incident_dir = data_dir / "traffic_incident_details"
    if incident_dir.exists():
        for fp in incident_dir.glob("*.md"):
            try:
                evt = _parse_single_event(fp)
                if evt:
                    events.append(evt)
            except Exception as e:
                logger.warning(f"Failed to parse {fp.name}: {e}")

    logger.info(f"Loaded {len(events)} construction/incident events")
    return events


def _parse_single_event(filepath: Path) -> Optional[ConstructionEvent]:
    """Parse a single event file."""
    filename = filepath.name
    content = filepath.read_text(encoding="utf-8", errors="replace")

    # Try filename parsing first
    name_k = parse_filename_k_values(filename)
    if not name_k:
        return None

    hw_name, k_start, k_end = name_k

    # Map to highway code
    hw_code = HIGHWAY_NAME_MAP.get(hw_name, "")
    if not hw_code:
        # Try partial match
        for name, code in HIGHWAY_NAME_MAP.items():
            if name in hw_name or hw_name in name:
                hw_code = code
                break
    if not hw_code:
        # Fallback: use the Chinese name as code
        hw_code = hw_name

    # Parse content for additional fields
    meta = parse_markdown_content(content)

    return ConstructionEvent(
        filename=filename,
        highway_name=hw_name,
        highway_code=hw_code,
        k_start=min(k_start, k_end),  # Normalize: start ≤ end
        k_end=max(k_start, k_end),
        direction=meta.get("direction", "未知方向"),
        event_time=meta.get("event_time", ""),
        description=meta.get("description", ""),
        url=meta.get("url", ""),
    )


def match_events_to_route(
    route_highway_codes: list[str],
    route_segments: Optional[list[dict]] = None,
    events: Optional[list[ConstructionEvent]] = None,
) -> dict:
    """Match construction events to a planned route.

    Args:
        route_highway_codes: List of highway codes on the route, e.g. ["G1517", "G15", "S53"]
        route_segments: Optional detailed segments with K-ranges
            [{"highway_code": "G15", "k_from": 2130.0, "k_to": 2323.0}, ...]
        events: Pre-loaded events (loads from disk if None)

    Returns:
        {
            "total_events": int,
            "matching_events": int,
            "matches": [...],        # Events that overlap with route segments
            "highway_events": [...], # All events on route highways (no K check)
            "warnings": [...],
        }
    """
    if events is None:
        events = load_all_events()

    codes_set = set(route_highway_codes)

    # Filter events by highway code
    highway_events = [e for e in events if e.highway_code in codes_set]
    highway_events.sort(key=lambda e: e.k_start)

    # If we have segment K-ranges, do precise matching
    matching = []
    warnings = []

    if route_segments:
        for evt in highway_events:
            for seg in route_segments:
                if seg.get("highway_code", "") != evt.highway_code:
                    continue
                k_from = seg.get("k_from", 0)
                k_to = seg.get("k_to", 0)
                k_min = min(k_from, k_to)
                k_max = max(k_from, k_to)

                # Check if event K-range overlaps with segment K-range
                if evt.k_end >= k_min and evt.k_start <= k_max:
                    # Calculate overlap
                    overlap_start = max(evt.k_start, k_min)
                    overlap_end = min(evt.k_end, k_max)
                    overlap_pct = (
                        (overlap_end - overlap_start) / (evt.k_end - evt.k_start) * 100
                        if evt.k_end > evt.k_start else 100.0
                    )

                    matching.append({
                        "event": evt,
                        "segment": seg,
                        "overlap_pct": round(overlap_pct, 1),
                    })

                    # Generate warning
                    severity = "严重" if overlap_pct > 50 else "轻微"
                    warnings.append(
                        f"[{severity}] {evt.highway_code} {evt.highway_name} "
                        f"K{evt.k_start:.0f}+{int((evt.k_start%1)*1000):03d}"
                        f"~K{evt.k_end:.0f}+{int((evt.k_end%1)*1000):03d}: "
                        f"{evt.description or '施工/事件'} ({evt.direction})"
                    )

    # Remove duplicates (same event matching multiple segments)
    seen = set()
    unique_matches = []
    for m_item in matching:
        key = m_item["event"].filename
        if key not in seen:
            seen.add(key)
            unique_matches.append(m_item)

    return {
        "total_events": len(events),
        "total_on_route_highways": len(highway_events),
        "matching_events": len(unique_matches),
        "matches": unique_matches,
        "highway_events": highway_events,
        "warnings": warnings,
    }


def format_events_for_llm(match_result: dict, max_items: int = 15) -> str:
    """Format matched events into text for the LLM prompt."""
    if not match_result or match_result.get("matching_events", 0) == 0:
        return ""

    lines = [
        "【施工/事件精确匹配结果】",
        f"路线涉及高速共找到 {match_result['total_on_route_highways']} 条施工/事件记录",
    ]

    matches = match_result.get("matches", [])
    if matches:
        lines.append(f"其中 {len(matches)} 条与路线段落精确重叠:")
        lines.append("")

        for m_item in matches[:max_items]:
            evt = m_item["event"]
            seg = m_item["segment"]
            k_str_start = f"K{evt.k_start:.0f}+{int((evt.k_start%1)*1000):03d}"
            k_str_end = f"K{evt.k_end:.0f}+{int((evt.k_end%1)*1000):03d}"
            lines.append(
                f"  • {evt.highway_code} {evt.highway_name} "
                f"{k_str_start}~{k_str_end}"
            )
            lines.append(f"    方向: {evt.direction} | 时间: {evt.event_time}")
            lines.append(f"    内容: {evt.description or '暂无描述'}")
            lines.append(f"    重叠度: {m_item['overlap_pct']}%")
            lines.append("")
    else:
        # No K-range overlap, list all events on the route highways
        lines.append("以下为该路线高速上的事件（未验证K值重叠）:")
        lines.append("")
        for evt in match_result.get("highway_events", [])[:max_items]:
            k_str_start = f"K{evt.k_start:.0f}+{int((evt.k_start%1)*1000):03d}"
            k_str_end = f"K{evt.k_end:.0f}+{int((evt.k_end%1)*1000):03d}"
            lines.append(
                f"  • {evt.highway_code} {evt.highway_name} "
                f"{k_str_start}~{k_str_end}: {evt.description or '暂无描述'}"
            )

    if match_result.get("warnings"):
        lines.append("")
        lines.append("[!!] 施工警告:")
        for w in match_result["warnings"][:10]:
            lines.append(f"  {w}")

    return "\n".join(lines)


# Singleton-style helper
construction_matcher = type("Matcher", (), {
    "load_all_events": staticmethod(load_all_events),
    "match_events_to_route": staticmethod(match_events_to_route),
    "format_events_for_llm": staticmethod(format_events_for_llm),
})()
