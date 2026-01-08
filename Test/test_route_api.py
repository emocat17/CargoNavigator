import httpx
import asyncio

async def test_route_api():
    url = "http://localhost:9876/api/v1/routes/plan"
    payload = {
        "origin": "北京市朝阳区阜通东大街6号",
        "destination": "北京市海淀区海淀公园",
        "vehicle": {
            "length": 13.5,
            "width": 2.55,
            "height": 4.0,
            "weight": 49.0,
            "axis_weight": 10.0
        },
        "strategy": 0
    }
    
    print(f"Testing POST {url}...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                routes = data.get("data", {}).get("routes", [])
                print(f"✅ Success! Found {len(routes)} routes.")
                if routes:
                    print(f"   Route 1 distance: {routes[0]['distance']}m")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_route_api())
