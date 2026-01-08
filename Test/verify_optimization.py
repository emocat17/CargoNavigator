import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Set dummy API key for testing to pass Pydantic validation
os.environ["AMAP_API_KEY"] = "dummy_key_for_test"

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'SmartRoute', 'backend'))

# We need to mock amap_service before importing routes if routes imports it directly
# But routes imports the module, so we can patch it after import or before.
# Let's import first.
from app.services.amap_service import AmapService
from app.models.schemas import RoutePlanRequest

async def test_optimization_fields():
    print("Starting optimization verification...")

    # Mock Amap Response
    # This structure matches what the Amap API returns for a driving route
    mock_amap_response = {
        "status": "1",
        "info": "OK",
        "route": {
            "paths": [
                {
                    "distance": "5000",
                    "duration": "15000", # > 4 hours (14400)
                    "strategy": "速度最快",
                    "tolls": "10",
                    "toll_distance": "1000",
                    "traffic_lights": "5",
                    "restriction": "0",
                    "steps": [
                        {
                            "instruction": "进入秦岭隧道",
                            "road": "秦岭隧道",
                            "distance": "2000",
                            "duration": "120",
                            "polyline": "116.481028,39.989643",
                            "action": "直行",
                            "assistant_action": "开启车灯",
                            "tmcs": [
                                {"status": "拥堵", "polyline": "..."}
                            ]
                        },
                        {
                            "instruction": "直行进入主路",
                            "road": "高速主路",
                            "distance": "3000",
                            "duration": "300",
                            "polyline": "116.481028,39.989643",
                            "action": "直行",
                            "assistant_action": "",
                            "tmcs": [
                                {"status": "畅通", "polyline": "..."}
                            ]
                        }
                    ]
                }
            ]
        }
    }

    # Mock the service method
    # Note: search_route calls AmapService.plan_route_driving(request)
    AmapService.plan_route_driving = AsyncMock(return_value=mock_amap_response)
    
    # Import the function to test
    from app.api.routes import plan_route
    
    req = RoutePlanRequest(
        origin="116.481028,39.989643",
        destination="116.434446,39.90816",
        strategy=0,
        vehicle=None
    )

    try:
        # Call the actual business logic
        result = await plan_route(req)
        
        # Verify results
        # plan_route returns RoutePlanResponse, which has data field
        # data is Dict[str, List[RouteInfo]]
        # We need to access result.data['routes'][0] if that's the structure
        # Wait, check RoutePlanResponse definition
        
        # RoutePlanResponse: data: Dict[str, List[RouteInfo]]
        # Usually it returns `routes` key.
        # Let's check `routes.py` return value.
        # It returns `RoutePlanResponse(data={"routes": routes})` or similar.
        # Wait, `routes.py` returns `RoutePlanResponse`.
        
        # In routes.py:
        # return RoutePlanResponse(data={"routes": routes}) (implicit or explicit)
        # Actually it returns `routes` list in some cases or object.
        # @router.post(..., response_model=RoutePlanResponse)
        # function returns RoutePlanResponse object or dict.
        
        # Let's check what plan_route returns in python code (not via HTTP)
        # It probably returns the Pydantic model instance.
        
        routes_list = result.data.get("routes", [])
        if not routes_list:
            print("FAILURE: No routes returned")
            return

        route_info = routes_list[0]
        
        print(f"Route Duration: {route_info.duration} (Expected: 15000)")
        print(f"Tunnel Count: {route_info.tunnel_count} (Expected: 1)")
        print(f"Tunnel Distance: {route_info.tunnel_distance} (Expected: 2000)")
        
        step0 = route_info.steps[0]
        print(f"Step 0 Traffic Status: {step0.traffic_status} (Expected: 拥堵)")
        print(f"Step 0 Assistant Action: {step0.assistant_action} (Expected: 开启车灯)")
        
        step1 = route_info.steps[1]
        print(f"Step 1 Traffic Status: {step1.traffic_status} (Expected: 畅通)")

        if (route_info.tunnel_count == 1 and 
            step0.traffic_status == "拥堵" and 
            route_info.duration == 15000 and 
            step0.assistant_action == "开启车灯"):
            print("SUCCESS: Optimization fields verified correctly.")
        else:
            print("FAILURE: Fields do not match expectations.")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_optimization_fields())
