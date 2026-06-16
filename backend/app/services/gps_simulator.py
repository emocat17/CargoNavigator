"""GPS Simulator — generates mock GPS positions along Amap route polylines."""
import asyncio
import logging
import math
import random
import time as time_mod
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

TZ_UTC8 = timezone(timedelta(hours=8))


def _now_utc8() -> datetime:
    return datetime.now(TZ_UTC8)


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    dlon = math.radians(lon2 - lon1)
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2r)
    y = (math.cos(lat1r) * math.sin(lat2r) -
         math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon))
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


class GPSSimulator:
    """Simulate GPS movement along an Amap polyline."""

    def __init__(self, polyline: str, checkpoints: list[dict], speed_kmh: float = 60.0):
        if not polyline or not polyline.strip():
            raise ValueError("polyline must not be empty")

        self.speed_kmh = speed_kmh
        self.speed_ms = speed_kmh / 3.6

        self.coords: list[tuple[float, float]] = []
        for pair in polyline.split(";"):
            pair = pair.strip()
            if not pair:
                continue
            parts = pair.split(",")
            if len(parts) >= 2:
                self.coords.append((float(parts[0]), float(parts[1])))

        if len(self.coords) < 2:
            raise ValueError("polyline must have at least 2 coordinates")

        self.cumulative_distances: list[float] = [0.0]
        for i in range(1, len(self.coords)):
            prev = self.coords[i - 1]
            curr = self.coords[i]
            d = _haversine_m(prev[0], prev[1], curr[0], curr[1])
            self.cumulative_distances.append(self.cumulative_distances[-1] + d)

        self.total_distance_m = self.cumulative_distances[-1]
        self.checkpoints = checkpoints
        self.passed_checkpoints: set[str] = set()

    async def run(self) -> AsyncGenerator[dict, None]:
        start_time = time_mod.monotonic()
        segment_duration = 5.0

        while True:
            elapsed = time_mod.monotonic() - start_time
            pos = self.calculate_position(elapsed)

            if pos["distance_remaining"] <= 0:
                pos["distance_remaining"] = 0
                pos["speed"] = 0
                yield {"type": "gps", **pos}
                break

            yield {"type": "gps", **pos}

            nearby = self.check_nearby_checkpoints({"lon": pos["lon"], "lat": pos["lat"]})
            for cp in nearby:
                yield {
                    "type": "checkpoint",
                    "station": cp["station"],
                    "checkpoint_type": cp["type"],
                    "highway": cp.get("highway", ""),
                    "passed_at": _now_utc8().isoformat(),
                }

            if random.random() < 0.04:
                anomaly = self._generate_anomaly(pos)
                if anomaly:
                    yield {"type": "alert", **anomaly}

            await asyncio.sleep(segment_duration)

        yield {"type": "done"}

    def calculate_position(self, elapsed_seconds: float) -> dict:
        distance_traveled = self.speed_ms * elapsed_seconds
        distance_traveled = min(distance_traveled, self.total_distance_m)

        dists = self.cumulative_distances
        lo, hi = 0, len(dists) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if dists[mid] < distance_traveled:
                lo = mid + 1
            else:
                hi = mid

        seg_idx = max(0, lo - 1)
        if seg_idx >= len(self.coords) - 1:
            seg_idx = len(self.coords) - 2

        seg_start_dist = dists[seg_idx]
        seg_end_dist = dists[seg_idx + 1]
        seg_length = seg_end_dist - seg_start_dist
        t = ((distance_traveled - seg_start_dist) / seg_length) if seg_length > 0 else 0
        t = max(0.0, min(1.0, t))

        lon1, lat1 = self.coords[seg_idx]
        lon2, lat2 = self.coords[seg_idx + 1]
        lon = lon1 + t * (lon2 - lon1)
        lat = lat1 + t * (lat2 - lat1)

        heading = _bearing(lon1, lat1, lon2, lat2)
        remaining_km = max(0, (self.total_distance_m - distance_traveled) / 1000)

        return {
            "lon": round(lon, 6),
            "lat": round(lat, 6),
            "speed": round(self.speed_kmh + random.uniform(-3, 3), 1),
            "heading": round(heading, 1),
            "timestamp": _now_utc8().isoformat(),
            "distance_remaining": round(remaining_km, 2),
        }

    def check_nearby_checkpoints(self, current_pos: dict) -> list[dict]:
        found = []
        for cp in self.checkpoints:
            key = cp["station"]
            if key in self.passed_checkpoints:
                continue
            cp_lon = cp.get("lon") or cp.get("longitude")
            cp_lat = cp.get("lat") or cp.get("latitude")
            if cp_lon is None or cp_lat is None:
                continue
            dist = _haversine_m(current_pos["lon"], current_pos["lat"],
                               float(cp_lon), float(cp_lat))
            if dist < 200:
                self.passed_checkpoints.add(key)
                found.append(cp)
        return found

    def _generate_anomaly(self, current_pos: dict) -> Optional[dict]:
        anomaly_type = random.choice(["speed", "deviation", "stop"])
        now_iso = _now_utc8().isoformat()

        if anomaly_type == "speed":
            fake_speed = self.speed_kmh + random.uniform(20, 40)
            return {
                "alert_type": "speed",
                "message": f"超速警告: 当前速度{fake_speed:.0f}km/h (限速{self.speed_kmh:.0f}km/h)",
                "severity": random.choice(["medium", "high"]),
                "longitude": str(current_pos["lon"]),
                "latitude": str(current_pos["lat"]),
                "timestamp": now_iso,
            }
        elif anomaly_type == "deviation":
            return {
                "alert_type": "deviation",
                "message": f"偏航警告: 车辆偏离路线约{random.randint(30, 80)}米",
                "severity": "high",
                "longitude": str(current_pos["lon"]),
                "latitude": str(current_pos["lat"]),
                "timestamp": now_iso,
            }
        elif anomaly_type == "stop":
            return {
                "alert_type": "stop",
                "message": "异常停车: 速度低于5km/h已持续30秒",
                "severity": "medium",
                "longitude": str(current_pos["lon"]),
                "latitude": str(current_pos["lat"]),
                "timestamp": now_iso,
            }
        return None
