
import sys
import os
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "SmartRoute" / "backend"
sys.path.append(str(backend_path))

from app.services.amap_service import AmapService

async def test_amap_service():
    print("Testing AmapService...")
    
    # 1. Test Geocoding
    address = "北京市朝阳区阜通东大街6号"
    print(f"1. Testing Geocoding for '{address}'...")
    coords = await AmapService.get_geo_code(address)
    print(f"   Result: {coords}")
    
    if coords:
        print("   ✅ Geocoding Passed")
    else:
        print("   ❌ Geocoding Failed")

    # 2. Test Route Planning
    if coords:
        origin = f"{coords[0]},{coords[1]}"
        destination = "116.480983,39.989628" # A random nearby point
        
        print(f"\n2. Testing Route Planning from {origin} to {destination}...")
        route_result = await AmapService.plan_route_driving(origin, destination)
        
        if route_result.get("status") == "1":
            route_data = route_result.get("route", {})
            paths = route_data.get("paths", [])
            print(f"   Success! Found {len(paths)} routes.")
            if paths:
                print(f"   First route distance: {paths[0]['distance']}m")
                print("   ✅ Route Planning Passed")
        else:
            print(f"   ❌ Route Planning Failed: {route_result.get('info')}")

if __name__ == "__main__":
    asyncio.run(test_amap_service())
