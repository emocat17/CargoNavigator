import requests
import json

def test_route_optimization():
    url = "http://localhost:9876/api/v1/routes/plan"
    payload = {
        "origin": "117.412021,26.291825",
        "destination": "119.720309,25.473174",
        "strategy": 0,
        "vehicle": {
            "length": 13.5,
            "width": 2.55,
            "height": 4.0,
            "weight": 49.0,
            "axis_weight": 10.0
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            routes = data.get("data", {}).get("routes", [])
            if routes:
                route = routes[0]
                print(f"Passed Cities: {route.get('passed_cities')}")
                print(f"Toll Roads: {route.get('toll_roads_details')}")
                
                if "passed_cities" in route and "toll_roads_details" in route:
                    print("✅ Verification Successful: New fields are present.")
                else:
                    print("❌ Verification Failed: New fields missing.")
            else:
                print("❌ No routes returned.")
        else:
            print(f"❌ Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error during request: {e}")

if __name__ == "__main__":
    test_route_optimization()
