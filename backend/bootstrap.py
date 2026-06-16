"""
Pre-flight bootstrap: validates everything is ready before starting the server.

Run: python bootstrap.py
Or: python -c "from bootstrap import ensure_ready; ensure_ready()"
"""
import sys
import os
from pathlib import Path

CHECKS_PASSED = 0
CHECKS_FAILED = 0


def ok(msg: str):
    global CHECKS_PASSED
    CHECKS_PASSED += 1
    print(f"  [OK] {msg}")


def warn(msg: str):
    global CHECKS_FAILED
    CHECKS_FAILED += 1
    print(f"  [WARN] {msg}")


def ensure_ready():
    print("=" * 60)
    print("CargoNavigator Bootstrap")
    print("=" * 60)

    # ── 1. Bridge Database ──
    print("\n[1/4] Bridge Database (桥梁数据库)")
    try:
        from app.bridge_db import init_bridge_db, query
        init_bridge_db()
        result = query("SELECT COUNT(*) as cnt FROM bridges")
        bridge_count = result[0]["cnt"] if result else 0
        result2 = query("SELECT COUNT(*) as cnt FROM bridge_influence_lines")
        il_count = result2[0]["cnt"] if result2 else 0
        ok(f"Bridge DB ready: {bridge_count} bridges, {il_count} influence lines")
    except Exception as e:
        warn(f"Bridge DB unavailable: {e}")
        print("    -> Run: python -m data.migrate_data")

    # ── 2. Spider Data ──
    print("\n[2/4] Spider Data (爬虫施工数据)")
    spider_dir = Path(__file__).parent / "spider" / "data" / "road_details"
    construction_dir = spider_dir / "road_construction_details"
    incident_dir = spider_dir / "traffic_incident_details"

    const_count = len(list(construction_dir.glob("*.md"))) if construction_dir.exists() else 0
    inc_count = len(list(incident_dir.glob("*.md"))) if incident_dir.exists() else 0
    total = const_count + inc_count

    if total > 0:
        ok(f"Spider data ready: {const_count} construction + {inc_count} incident events")
    else:
        warn("Spider data empty. Run: python -m spider.main")

    # ── 3. LLM Configuration ──
    print("\n[3/4] LLM Configuration (大模型配置)")
    try:
        from app.core.config import settings
        if settings.DEEPSEEK_API_KEY:
            ok(f"DeepSeek configured: {settings.DEEPSEEK_MODEL} @ {settings.DEEPSEEK_BASE_URL}")
        elif os.getenv("DEEPSEEK_API_KEY"):
            ok(f"DeepSeek configured from env: {os.getenv('DEEPSEEK_MODEL', 'unknown')}")
        else:
            warn("DEEPSEEK_API_KEY not set. Agent features will fail.")
    except Exception as e:
        warn(f"Config check failed: {e}")

    # ── 4. Amap API ──
    print("\n[4/4] Amap API (高德地图)")
    if settings.AMAP_API_KEY:
        ok(f"Amap API key configured")
    else:
        warn("AMAP_API_KEY not set. Route planning will fail.")

    # ── Summary ──
    print("\n" + "=" * 60)
    total = CHECKS_PASSED + CHECKS_FAILED
    if CHECKS_FAILED == 0:
        print(f"All {total} checks passed. Ready to serve.")
    else:
        print(f"{CHECKS_PASSED}/{total} passed, {CHECKS_FAILED} warnings.")
        print("Server will start but some features may be unavailable.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    ensure_ready()
