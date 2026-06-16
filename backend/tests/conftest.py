"""
Shared pytest fixtures for CargoNavigator backend tests.
"""
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so that 'app' imports work.
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_vehicle() -> dict:
    """A representative heavy-cargo vehicle."""
    return {
        "axle_loads_ton": [10, 15, 12],    # tons
        "axle_spacings": [3.5, 1.2],        # meters
    }


@pytest.fixture
def sample_route_text() -> str:
    """A realistic route description as returned by the route planner."""
    return (
        "**方案1**: 285.0km, 约240分钟, 过路费¥180, 路况:畅通\n"
        "  路径: 三明--G1517莆炎高速--港后枢纽--G15沈海高速--海沧枢纽--S53渔平支线--平潭\n"
        "  隧道: 53个, 总长45.2km\n"
        "  主要道路: G1517莆炎高速 → G15沈海高速 → S53渔平支线"
    )


@pytest.fixture
def sample_highway_codes() -> list[str]:
    """Highway codes extracted from sample_route_text."""
    return ["G1517", "G15", "S53"]


@pytest.fixture
def bridge_db_exists() -> bool:
    """Return True when the cargo_bridge.db file is present."""
    db_path = Path(__file__).parent.parent / "data" / "cargo_bridge.db"
    return db_path.exists()
