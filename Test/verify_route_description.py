import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:9876/api/v1/routes/plan"

def verify_route_description():
    print(f"Testing Route Description Generation...")
    
    # Use user provided addresses to verify label replacement and path details
    origin_addr = "福建省三明厦钨新能源"
    dest_addr = "福建省平潭跨境电商园"
    
    payload = {
        "origin": origin_addr, 
        "destination": dest_addr, 
        "vehicle": {
            "length": 13.5,
            "width": 2.55,
            "height": 4.0,
            "weight": 49.0,
            "axis_weight": 10.0
        }
    }
    
    try:
        resp = requests.post(BASE_URL, json=payload)
        if resp.status_code == 200:
            data = resp.json()["data"]["routes"]
            print(f"Got {len(data)} routes.")
            
            for i, r in enumerate(data):
                desc = r.get("route_description", "")
                print(f"\nRoute {i+1} Description: {desc}")
                
                # Check Labels
                if origin_addr in desc and dest_addr in desc:
                     print(f"PASS: Route {i+1} uses user input labels.")
                else:
                     print(f"FAIL: Route {i+1} labels mismatch. Expected {origin_addr}/{dest_addr}")

                # Check Redundancy
                if "沿吉口互通--吉口互通" in desc:
                     print(f"FAIL: Redundancy found: 沿吉口互通--吉口互通")
                else:
                     print(f"PASS: '沿吉口互通--吉口互通' redundancy check.")

                # Check G1517 Repetition
                # Count occurrences of "G1517莆炎高速"
                # Note: It might appear if the route enters/exits? But user complained about it.
                # In the improved logic, it should appear once if continuous.
                count_g1517 = desc.count("G1517莆炎高速")
                if count_g1517 <= 1:
                     print(f"PASS: G1517 Repetition check (Count: {count_g1517}).")
                else:
                     # Warn but don't fail hard if it's actually separated by other main roads
                     # But for this route we expect 1.
                     print(f"WARN: G1517 appears {count_g1517} times. Check if redundant.")
                     
                # Check Aux Road Redundancy
                if "金井湾大道--金井湾大道辅路" in desc:
                     print(f"FAIL: Redundancy found: 金井湾大道--金井湾大道辅路")
                elif "金井湾大道辅路" in desc and "金井湾大道" in desc:
                     # Check if they are adjacent
                     print(f"WARN: Both Main and Aux present. Check adjacency.")
                else:
                     print(f"PASS: Aux Road redundancy check.")

        else:
            print(f"FAIL: API Error {resp.status_code} - {resp.text}")

    except Exception as e:
        print(f"FAIL: Exception {e}")

if __name__ == "__main__":
    verify_route_description()
