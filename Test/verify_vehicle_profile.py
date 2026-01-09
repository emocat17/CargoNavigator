import requests
import json
import sys

BASE_URL = "http://localhost:9876/api/v1/vehicles"

def test_vehicle_lifecycle():
    print("Testing Vehicle Profile Lifecycle...")
    
    # 1. Create
    payload = {
        "name": "Test Heavy Truck",
        "length": 18.0,
        "width": 2.5,
        "height": 4.0,
        "total_weight": 49.0,
        "axis_count": 6,
        "axis_weights": [7.0, 7.0, 11.5, 11.5, 11.5, 11.5],
        "axis_distances": [3.2, 1.4, 7.0, 1.4, 1.4],
        "tire_count": 22,
        "cargo_type": "Machinery"
    }
    
    print(f"Creating profile: {payload['name']}")
    try:
        response = requests.post(BASE_URL + "/", json=payload)
        response.raise_for_status()
        vehicle = response.json()
        print(f"[PASS] Created Vehicle ID: {vehicle['id']}")
    except Exception as e:
        print(f"[FAIL] Create failed: {e}")
        print(response.text if 'response' in locals() else "No response")
        return

    vehicle_id = vehicle['id']

    # 2. Read List
    try:
        response = requests.get(BASE_URL + "/")
        response.raise_for_status()
        profiles = response.json()
        found = any(p['id'] == vehicle_id for p in profiles)
        if found:
            print(f"[PASS] Vehicle found in list (Total: {len(profiles)})")
        else:
            print("[FAIL] Vehicle not found in list")
    except Exception as e:
        print(f"[FAIL] List failed: {e}")

    # 3. Read Single
    try:
        response = requests.get(f"{BASE_URL}/{vehicle_id}")
        response.raise_for_status()
        v_data = response.json()
        if v_data['axis_weights'] == payload['axis_weights']:
            print("[PASS] Read single profile detail correct")
        else:
            print("[FAIL] Read detail mismatch")
    except Exception as e:
        print(f"[FAIL] Read single failed: {e}")

    # 4. Update
    update_payload = {"name": "Updated Truck Name"}
    try:
        response = requests.put(f"{BASE_URL}/{vehicle_id}", json=update_payload)
        response.raise_for_status()
        updated = response.json()
        if updated['name'] == "Updated Truck Name":
            print("[PASS] Update successful")
        else:
            print("[FAIL] Update name mismatch")
    except Exception as e:
        print(f"[FAIL] Update failed: {e}")

    # 5. Delete
    try:
        response = requests.delete(f"{BASE_URL}/{vehicle_id}")
        if response.status_code == 204:
            print("[PASS] Delete successful")
        else:
            print(f"[FAIL] Delete status code: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Delete failed: {e}")

    # Verify Delete
    response = requests.get(f"{BASE_URL}/{vehicle_id}")
    if response.status_code == 404:
        print("[PASS] Vehicle correctly gone after delete")
    else:
        print(f"[FAIL] Vehicle still exists: {response.status_code}")

if __name__ == "__main__":
    test_vehicle_lifecycle()
