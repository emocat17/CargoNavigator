"""Tests for gps_simulator.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.services.gps_simulator import GPSSimulator


SAMPLE_POLYLINE = (
    "119.296,26.074;119.297,26.075;119.298,26.076;"
    "119.300,26.078;119.302,26.080;119.305,26.083"
)

SAMPLE_CHECKPOINTS = [
    {"station": "K100+000", "type": "bridge", "highway": "G15", "lon": 119.298, "lat": 26.076},
    {"station": "K105+000", "type": "tunnel", "highway": "G15", "lon": 119.302, "lat": 26.080},
]


class TestGPSSimulatorInit:
    def test_parses_polyline_into_coordinates(self):
        sim = GPSSimulator(SAMPLE_POLYLINE, [])
        assert len(sim.coords) == 6
        assert sim.coords[0] == (119.296, 26.074)

    def test_builds_cumulative_distance_table(self):
        sim = GPSSimulator(SAMPLE_POLYLINE, [])
        assert len(sim.cumulative_distances) == 6
        assert sim.cumulative_distances[0] == 0.0
        assert sim.cumulative_distances[-1] > 0
        assert sim.total_distance_m > 0

    def test_empty_polyline_raises(self):
        with pytest.raises(ValueError, match="polyline"):
            GPSSimulator("", [])


class TestCalculatePosition:
    def test_start_position(self):
        sim = GPSSimulator(SAMPLE_POLYLINE, [])
        pos = sim.calculate_position(0)
        assert pos["lon"] == 119.296
        assert pos["lat"] == 26.074
        assert pos["speed"] > 0
        assert "heading" in pos
        assert "timestamp" in pos
        assert pos["distance_remaining"] > 0

    def test_end_position(self):
        sim = GPSSimulator(SAMPLE_POLYLINE, [])
        total_time = sim.total_distance_m / (60 / 3.6)
        pos = sim.calculate_position(total_time + 999)
        assert pos["lon"] == 119.305
        assert pos["lat"] == 26.083
        assert pos["distance_remaining"] <= 0

    def test_mid_position(self):
        sim = GPSSimulator(SAMPLE_POLYLINE, [])
        half_time = (sim.total_distance_m / (60 / 3.6)) / 2
        pos = sim.calculate_position(half_time)
        assert 119.296 < pos["lon"] < 119.305
        assert pos["distance_remaining"] < sim.total_distance_m / 1000


class TestCheckpointDetection:
    def test_detects_nearby_checkpoint(self):
        sim = GPSSimulator(SAMPLE_POLYLINE, SAMPLE_CHECKPOINTS)
        current = {"lon": 119.298001, "lat": 26.076001}
        found = sim.check_nearby_checkpoints(current)
        assert len(found) >= 1
        assert found[0]["station"] == "K100+000"

    def test_no_false_positive_far_from_checkpoint(self):
        sim = GPSSimulator(SAMPLE_POLYLINE, SAMPLE_CHECKPOINTS)
        current = {"lon": 119.296, "lat": 26.074}
        found = sim.check_nearby_checkpoints(current)
        assert len(found) == 0

    def test_detects_multiple_nearby(self):
        cps = [
            {"station": "A", "type": "bridge", "highway": "G15", "lon": 119.300, "lat": 26.078},
            {"station": "B", "type": "tunnel", "highway": "G15", "lon": 119.300, "lat": 26.078},
        ]
        sim = GPSSimulator(SAMPLE_POLYLINE, cps)
        current = {"lon": 119.300001, "lat": 26.078001}
        found = sim.check_nearby_checkpoints(current)
        assert len(found) == 2
