"""
Highway Network Graph (SQL Edition).

Provides:
- Graph construction from road_sections table
- Path finding between junctions (DFS)
- Route-to-bridge mapping
- Coordinate-based nearest junction lookup
"""
import math
import logging
from typing import Optional

from app.bridge_db import query, query_one, get_bridge_db

logger = logging.getLogger(__name__)


def build_graph() -> dict[str, list[dict]]:
    """Build adjacency list from road_sections table.

    Returns: {junction_name: [{"junction": other_junction, "highway_code": hw, "k_from": k1, "k_to": k2}, ...]}
    """
    rows = query("""
        SELECT junction_from, junction_to, highway_code, k_from, k_to
        FROM road_sections
    """)

    graph: dict[str, list[dict]] = {}
    for r in rows:
        j1 = r["junction_from"]
        j2 = r["junction_to"]

        if j1 not in graph:
            graph[j1] = []
        if j2 not in graph:
            graph[j2] = []

        graph[j1].append({
            "junction": j2,
            "highway_code": r["highway_code"],
            "k_from": r["k_from"],
            "k_to": r["k_to"],
        })
        # Reverse direction (roads are bidirectional)
        graph[j2].append({
            "junction": j1,
            "highway_code": r["highway_code"],
            "k_from": r["k_to"],
            "k_to": r["k_from"],
        })

    return graph


def find_all_paths(
    start_junction: str,
    end_junction: str,
    max_depth: int = 12,
    max_paths: int = 50,
) -> list[dict]:
    """Find all paths between two junctions using DFS.

    Returns: list of {"path_string": "港后-G15-海沧-G76-青礁", "segments": [...]}
    """
    graph = build_graph()

    if start_junction not in graph:
        return []
    if end_junction not in graph:
        return []

    all_paths = []

    def dfs(current: str, path: list, visited: set):
        if len(all_paths) >= max_paths:
            return
        if len(path) > max_depth:
            return

        if current == end_junction and len(path) >= 2:
            # Build path string and segments
            segments = []
            path_str = start_junction
            for i in range(len(path) - 1):
                j_a = path[i]
                j_b = path[i + 1]
                # Find the edge
                for edge in graph.get(j_a, []):
                    if edge["junction"] == j_b:
                        hw = edge["highway_code"]
                        path_str += f"-{hw}-{j_b}"
                        segments.append({
                            "junction_from": j_a,
                            "junction_to": j_b,
                            "highway_code": hw,
                            "k_from": edge["k_from"],
                            "k_to": edge["k_to"],
                        })
                        break
                else:
                    return  # edge not found, invalid path

            all_paths.append({
                "path_string": path_str,
                "segments": segments,
                "length": len(segments),
            })
            return

        for edge in graph.get(current, []):
            neighbor = edge["junction"]
            if neighbor not in visited:
                visited.add(neighbor)
                path.append(neighbor)
                dfs(neighbor, path, visited)
                path.pop()
                visited.remove(neighbor)

    visited = {start_junction}
    dfs(start_junction, [start_junction], visited)

    # Sort by path length (fewer segments = shorter)
    all_paths.sort(key=lambda p: p["length"])
    return all_paths


def find_nearest_junction(lon: float, lat: float) -> Optional[dict]:
    """Find the nearest highway junction to a GPS coordinate.

    Returns: {"name": "港后", "lon": 119.21, "lat": 25.48, "distance_km": 5.3}
    """
    junctions = query("""
        SELECT junction_name, longitude, latitude
        FROM junctions
    """)

    if not junctions:
        return None

    best = None
    best_dist = float('inf')

    for j in junctions:
        dist = haversine(lon, lat, j["longitude"], j["latitude"])
        if dist < best_dist:
            best_dist = dist
            best = {
                "name": j["junction_name"],
                "lon": j["longitude"],
                "lat": j["latitude"],
                "distance_km": round(dist, 2),
            }

    return best


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate great-circle distance in km."""
    R = 6371.0
    dlon = math.radians(lon2 - lon1)
    dlat = math.radians(lat2 - lat1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def map_amap_route_to_junctions(
    amap_route_description: str,
    amap_major_roads: list[str],
) -> Optional[list[dict]]:
    """Attempt to map an Amap route to highway network junctions.

    Args:
        amap_route_description: e.g. "三明--G1517莆炎高速--港后枢纽--G15沈海高速..."
        amap_major_roads: e.g. ["G1517莆炎高速", "G15沈海高速"]

    Returns:
        List of highway segments with junctions, or None if mapping fails
    """
    segments = []
    highways = query("SELECT highway_code, highway_name FROM highways")

    # Build highway name → code map
    hw_map = {h["highway_name"]: h["highway_code"] for h in highways}
    hw_map.update({h["highway_code"]: h["highway_code"] for h in highways})

    # Extract highway codes from major_roads
    for road_str in amap_major_roads:
        # Try to find matching highway code
        found_hw = None
        for code in hw_map.values():
            if code in road_str:
                found_hw = code
                break
        if not found_hw:
            # Search by name
            for name, code in hw_map.items():
                if name and name in road_str:
                    found_hw = code
                    break

        if found_hw:
            segments.append({"highway_code": found_hw, "road_name": road_str})

    return segments if segments else None


def get_highway_info(highway_code: str) -> Optional[dict]:
    """Get highway name and category."""
    return query_one(
        "SELECT * FROM highways WHERE highway_code = ?",
        (highway_code,)
    )
