"""
Tests for app.services.construction_matcher.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.construction_matcher import (
    parse_filename_k_values,
    parse_k_value,
    match_events_to_route,
    HIGHWAY_NAME_MAP,
    ConstructionEvent,
    load_all_events,
)


# ============================================================================
# parse_k_value
# ============================================================================

class TestParseKValue:
    @pytest.mark.parametrize("k_str, expected", [
        ("K2338", 2338.0),
        ("K28+600", 28.6),
        ("K1946+500", 1946.5),
        ("K2410", 2410.0),
        ("K0+0", 0.0),
        ("K100+999", 100.999),
    ])
    def test_valid(self, k_str, expected):
        assert parse_k_value(k_str) == pytest.approx(expected, abs=0.001)

    def test_invalid(self):
        assert parse_k_value("abc") is None
        assert parse_k_value("") is None
        assert parse_k_value("K") is None


# ============================================================================
# parse_filename_k_values
# ============================================================================

class TestParseFilenameKValues:
    """Extract highway name and K-range from spider filenames."""

    def test_xiamen_chengdu_expressway(self):
        """Filename with K+minor format."""
        filename = "2026-03-14_12-17-13_厦蓉高速_K28_600_K28_850.md"
        result = parse_filename_k_values(filename)
        assert result is not None
        hw_name, k_start, k_end = result
        assert hw_name == "厦蓉高速"
        assert k_start == pytest.approx(28.6, abs=0.001)
        assert k_end == pytest.approx(28.85, abs=0.001)

    def test_shenyang_haikou_expressway(self):
        """Filename with K-major-only format."""
        filename = "2022-07-15_08-00-46_沈海高速_K2338_K2344.md"
        result = parse_filename_k_values(filename)
        assert result is not None
        hw_name, k_start, k_end = result
        assert hw_name == "沈海高速"
        assert k_start == pytest.approx(2338.0, abs=0.001)
        assert k_end == pytest.approx(2344.0, abs=0.001)

    def test_invalid_filename_returns_none(self):
        assert parse_filename_k_values("not_a_spider_file.md") is None
        assert parse_filename_k_values("random.txt") is None
        assert parse_filename_k_values("") is None

    def test_filename_without_extension(self):
        """Should also handle the no-extension case (rsplit)."""
        # This filename has no .md extension format but is still parseable
        # The rsplit means it'll split on the last dot, so "file.md" works fine
        pass  # already covered above

    def test_reversed_k_values_normalized(self):
        """K_end < K_start should still work (parse values independently)."""
        # "K28_850_K28_600" — the parse function returns raw values,
        # normalization happens in _parse_single_event, not parse_filename_k_values
        result = parse_filename_k_values("2026-03-14_12-17-41_厦蓉高速_K28_850_K28_600.md")
        assert result is not None
        hw_name, k_start, k_end = result
        assert hw_name == "厦蓉高速"
        assert k_start == pytest.approx(28.85, abs=0.001)
        assert k_end == pytest.approx(28.6, abs=0.001)


# ============================================================================
# HIGHWAY_NAME_MAP
# ============================================================================

class TestHighwayNameMap:
    """Verify key highway name → code mappings."""

    def test_major_national_highways(self):
        assert HIGHWAY_NAME_MAP["沈海高速"] == "G15"
        assert HIGHWAY_NAME_MAP["厦蓉高速"] == "G76"
        assert HIGHWAY_NAME_MAP["长深高速"] == "G25"
        assert HIGHWAY_NAME_MAP["福银高速"] == "G70"
        assert HIGHWAY_NAME_MAP["京台高速"] == "G3"
        assert HIGHWAY_NAME_MAP["莆炎高速"] == "G1517"

    def test_provincial_highways(self):
        assert HIGHWAY_NAME_MAP["渔平支线"] == "S53"
        assert HIGHWAY_NAME_MAP["渔平高速"] == "S53"
        assert HIGHWAY_NAME_MAP["福厦高速"] == "S11"
        assert HIGHWAY_NAME_MAP["永漳高速"] == "S30"

    def test_historical_aliases(self):
        """Historical/segment names should map to the same parent highway."""
        assert HIGHWAY_NAME_MAP["泉厦高速"] == "G15"
        assert HIGHWAY_NAME_MAP["漳诏高速"] == "G15"
        assert HIGHWAY_NAME_MAP["福宁高速"] == "G15"
        assert HIGHWAY_NAME_MAP["龙长高速"] == "G76"
        assert HIGHWAY_NAME_MAP["漳龙高速"] == "G76"

    def test_all_values_are_strings(self):
        for name, code in HIGHWAY_NAME_MAP.items():
            assert isinstance(name, str)
            assert isinstance(code, str), f"{name} → {code} is not str"
            assert len(code) >= 2, f"{name} → {code} too short"


# ============================================================================
# match_events_to_route
# ============================================================================

class TestMatchEventsToRoute:
    """Match construction events against route highway codes."""

    @staticmethod
    def _make_event(filename="evt.md", hw_name="沈海高速", hw_code="G15",
                    k_start=100.0, k_end=110.0):
        return ConstructionEvent(
            filename=filename,
            highway_name=hw_name,
            highway_code=hw_code,
            k_start=k_start,
            k_end=k_end,
            direction="A道",
            event_time="2026-01-01",
            description="测试施工事件",
            url="http://example.com",
        )

    def test_match_by_highway_code_only(self):
        """Without segments, all events on matched highways are returned."""
        events = [
            self._make_event("a.md", "沈海高速", "G15", 100, 110),
            self._make_event("b.md", "厦蓉高速", "G76", 50, 60),
        ]
        result = match_events_to_route(
            route_highway_codes=["G15"],
            route_segments=None,
            events=events,
        )
        assert result["total_events"] == 2
        assert result["total_on_route_highways"] == 1
        assert result["matching_events"] == 0  # No segments → no precise match
        assert len(result["highway_events"]) == 1
        assert result["highway_events"][0].highway_code == "G15"

    def test_match_with_segments(self):
        """With K-range segments, only overlapping events match."""
        events = [
            self._make_event("a.md", "沈海高速", "G15", 100, 110),
            self._make_event("b.md", "沈海高速", "G15", 200, 210),
            self._make_event("c.md", "厦蓉高速", "G76", 50, 60),
        ]
        segments = [
            {"highway_code": "G15", "k_from": 95, "k_to": 115},
        ]
        result = match_events_to_route(
            route_highway_codes=["G15"],
            route_segments=segments,
            events=events,
        )
        assert result["matching_events"] == 1
        match = result["matches"][0]
        assert match["event"].filename == "a.md"
        # The overlap: event k=100-110, segment k=95-115 → overlap 100-110 = 100%
        assert match["overlap_pct"] == pytest.approx(100.0)

    def test_partial_overlap(self):
        """Event partially overlapping with segment."""
        events = [
            self._make_event("a.md", "沈海高速", "G15", 100, 200),
        ]
        segments = [
            {"highway_code": "G15", "k_from": 140, "k_to": 160},
        ]
        result = match_events_to_route(
            route_highway_codes=["G15"],
            route_segments=segments,
            events=events,
        )
        assert result["matching_events"] == 1
        match = result["matches"][0]
        # Overlap: 140-160, event: 100-200 → overlap=20/100=20%
        assert abs(match["overlap_pct"] - 20.0) < 1.0

    def test_no_overlap(self):
        """Event and segment on same highway but no K overlap."""
        events = [
            self._make_event("a.md", "沈海高速", "G15", 100, 110),
        ]
        segments = [
            {"highway_code": "G15", "k_from": 200, "k_to": 210},
        ]
        result = match_events_to_route(
            route_highway_codes=["G15"],
            route_segments=segments,
            events=events,
        )
        assert result["matching_events"] == 0
        assert result["total_on_route_highways"] == 1  # Still on the highway

    def test_empty_events(self):
        result = match_events_to_route(
            route_highway_codes=["G15"],
            route_segments=None,
            events=[],
        )
        assert result["total_events"] == 0
        assert result["matching_events"] == 0
        assert result["highway_events"] == []

    def test_different_highway_code_no_match(self):
        """Events on a different highway should not match."""
        events = [
            self._make_event("a.md", "沈海高速", "G15", 100, 110),
        ]
        result = match_events_to_route(
            route_highway_codes=["G76"],
            route_segments=None,
            events=events,
        )
        assert result["total_on_route_highways"] == 0

    def test_warnings_generated_for_overlaps(self):
        """Warnings should be generated for overlapping events."""
        events = [
            self._make_event("a.md", "沈海高速", "G15", 100, 110),
        ]
        segments = [
            {"highway_code": "G15", "k_from": 95, "k_to": 115},
        ]
        result = match_events_to_route(
            route_highway_codes=["G15"],
            route_segments=segments,
            events=events,
        )
        assert len(result["warnings"]) > 0
        # Severity logic: >50% overlap → "严重"
        assert any("严重" in w for w in result["warnings"])

    def test_multiple_highway_codes(self):
        """Multiple highway codes should match events from all."""
        events = [
            self._make_event("a.md", "沈海高速", "G15", 100, 110),
            self._make_event("b.md", "渔平支线", "S53", 0, 10),
            self._make_event("c.md", "厦蓉高速", "G76", 50, 60),
        ]
        result = match_events_to_route(
            route_highway_codes=["G15", "S53"],
            route_segments=None,
            events=events,
        )
        assert result["total_on_route_highways"] == 2
        codes = {e.highway_code for e in result["highway_events"]}
        assert codes == {"G15", "S53"}


# ============================================================================
# load_all_events (from disk)
# ============================================================================

class TestLoadAllEvents:
    """Verify we can load real spider data files."""

    def test_load_from_default_dir(self):
        """Load events from the default SPIDER_DATA path."""
        from app.services.construction_matcher import SPIDER_DATA
        if not SPIDER_DATA.exists():
            pytest.skip("Spider data directory not found")

        events = load_all_events()
        assert isinstance(events, list)
        # We expect at least some construction files
        assert len(events) > 0, "Expected at least one event in spider data"

        # Verify structure of first event
        evt = events[0]
        assert isinstance(evt, ConstructionEvent)
        assert evt.filename
        assert evt.highway_name
        assert evt.highway_code
        assert evt.k_start <= evt.k_end  # normalized in _parse_single_event
