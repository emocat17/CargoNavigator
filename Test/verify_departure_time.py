import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:9876/api/v1/routes/plan"

def test_departure_time():
    # 1. Test Night Departure
    # Calculate a future time that is 03:00 AM
    now = datetime.now()
    # If now is before 3AM, use today 3AM (might be past), if after, use tomorrow 3AM.
    # Actually, let's just pick tomorrow 03:00:00
    tomorrow = now + timedelta(days=1)
    night_time = tomorrow.replace(hour=3, minute=0, second=0, microsecond=0)
    night_str = night_time.isoformat()
    
    print(f"Testing Night Departure at: {night_str}")
    
    payload_night = {
        "origin": "117.817028,26.242318", # Sanming
        "destination": "119.790934,25.508581", # Pingtan
        "departure_time": night_str,
        "vehicle": {
            "length": 13.5,
            "width": 2.55,
            "height": 4.0,
            "weight": 49.0,
            "axis_weight": 10.0
        }
    }
    
    try:
        resp = requests.post(BASE_URL, json=payload_night)
        if resp.status_code == 200:
            data = resp.json()["data"]["routes"]
            print(f"Got {len(data)} routes.")
            has_night_tag = False
            for r in data:
                if "夜间行车" in r["tags"]:
                    has_night_tag = True
                    break
            
            if has_night_tag:
                print("PASS: Night Driving tag found for 03:00 AM departure.")
            else:
                print("FAIL: Night Driving tag NOT found for 03:00 AM departure.")
        else:
            print(f"FAIL: API Error {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"FAIL: Exception {e}")

    # 2. Test Day Departure
    day_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    day_str = day_time.isoformat()
    
    print(f"\nTesting Day Departure at: {day_str}")
    
    payload_day = {
        "origin": "117.817028,26.242318", 
        "destination": "119.790934,25.508581", 
        "departure_time": day_str,
        "vehicle": {
            "length": 13.5,
            "width": 2.55,
            "height": 4.0,
            "weight": 49.0,
            "axis_weight": 10.0
        }
    }
    
    try:
        resp = requests.post(BASE_URL, json=payload_day)
        if resp.status_code == 200:
            data = resp.json()["data"]["routes"]
            # Check duration. Sanming to Pingtan is ~2.5 - 3 hours.
            # 10:00 + 3h = 13:00. Should NOT be night driving.
            
            night_tag_present = False
            for r in data:
                if "夜间行车" in r["tags"]:
                    night_tag_present = True
                    # Debug info
                    print(f"Route {r['id']} has Night Driving tag. Duration: {r['duration']}s")
            
            if not night_tag_present:
                print("PASS: No Night Driving tag for 10:00 AM departure.")
            else:
                print("FAIL: Night Driving tag found for 10:00 AM departure (Unexpected).")
        else:
            print(f"FAIL: API Error {resp.status_code} - {resp.text}")

    except Exception as e:
        print(f"FAIL: Exception {e}")

if __name__ == "__main__":
    test_departure_time()
