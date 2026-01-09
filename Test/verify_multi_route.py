
import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "SmartRoute", "backend")))

# Set dummy API key
os.environ["AMAP_API_KEY"] = "dummy_key_for_test"

from app.api.routes import plan_route
from app.models.schemas import RoutePlanRequest
from app.services.amap_service import AmapService

# Mock Response Factory
def create_mock_response(strategy_id, distance, duration, tolls):
    return {
        "status": "1",
        "route": {
            "paths": [
                {
                    "distance": str(distance),
                    "duration": str(duration),
                    "tolls": str(tolls),
                    "traffic_lights": "10",
                    "steps": [],
                    "strategy": str(strategy_id)
                }
            ]
        }
    }

async def test_multi_route():
    print("Testing Multi-Route Aggregation...")
    
    # Mock AmapService.plan_route_driving
    # Scenario: 
    # Strategy 0 (Speed): 100km, 1h, 50rmb
    # Strategy 1 (Cost): 120km, 2h, 0rmb
    # Strategy 2 (Dist): 90km, 1.5h, 30rmb
    # Strategy 9 (Congestion): Same as Strategy 0 (should be deduped)
    
    async def mock_plan(origin, dest, strategy):
        if strategy == 0:
            return create_mock_response(0, 100000, 3600, 50)
        elif strategy == 1:
            return create_mock_response(1, 120000, 7200, 0)
        elif strategy == 2:
            return create_mock_response(2, 90000, 5400, 30)
        elif strategy == 9:
            return create_mock_response(9, 100000, 3600, 50) # Duplicate of 0
        return {"status": "0"}

    AmapService.plan_route_driving = AsyncMock(side_effect=mock_plan)
    AmapService.get_geo_code = AsyncMock(return_value=(116.0, 39.0))

    req = RoutePlanRequest(origin="116.0,39.0", destination="116.1,39.1", strategy=0)
    
    try:
        response = await plan_route(req)
        routes = response.data["routes"]
        
        print(f"Returned {len(routes)} routes.")
        
        # Expect 3 unique routes (0/9 merged, 1, 2)
        if len(routes) == 3:
            print("[PASS] Correct number of unique routes returned")
        else:
            print(f"[FAIL] Expected 3 unique routes, got {len(routes)}")
            
        # Check Deduping (Route with distance 100000 should have 2 tags)
        merged_route = next((r for r in routes if r.distance == 100000), None)
        if merged_route:
            print(f"Merged Route Tags: {merged_route.tags}")
            if "速度优先" in merged_route.tags and "躲避拥堵" in merged_route.tags:
                print("[PASS] Tags merged correctly")
            else:
                print("[FAIL] Tags not merged correctly")
        else:
            print("[FAIL] Merged route not found")
            
    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multi_route())
