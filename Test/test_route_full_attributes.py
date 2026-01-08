import pytest
import requests
import json

BASE_URL = "http://localhost:9876/api/v1"

def test_plan_route_full_attributes():
    payload = {
        "origin": "福建省三明厦钨新能源",
        "destination": "福建省平潭跨境电商园",
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
        response = requests.post(f"{BASE_URL}/routes/plan", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        
        routes = data["data"]["routes"]
        assert len(routes) > 0
        
        route = routes[0]
        # Verify new fields
        assert "toll_cost" in route
        assert "toll_distance" in route
        assert "traffic_lights" in route
        assert "strategy" in route
        assert "restriction" in route
        
        print(f"\nRoute found: Distance={route['distance']}m, Duration={route['duration']}s")
        print(f"Tolls: {route['toll_cost']} RMB, Traffic Lights: {route['traffic_lights']}")
        print(f"Strategy: {route['strategy']}, Restriction: {route['restriction']}")
        
    except requests.exceptions.ConnectionError:
        pytest.fail("Backend server not running on port 9876")
