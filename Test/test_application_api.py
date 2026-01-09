import requests
import json
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://localhost:9876/api/v1/applications"

def test_application_workflow():
    print("Testing Application Workflow...")
    
    # 1. Create Application
    payload = {
        "status": "DRAFT",
        "vehicle_info": {
            "tractor_plate_number": "京A88888",
            "tractor_model": "Volvo FH16",
            "tractor_cur_weight": 8.5,
            "axle_count": 6,
            "tire_count": 22,
            "axis_weights": [10.0, 15.0, 12.0],
            "axis_distances": [3.5, 1.2]
        },
        "owner_info": {
            "entity_name": "Fast Logistics Co.",
            "driver_name": "John Doe",
            "driver_telephone_number": "13800138000"
        },
        "cargo_info": {
            "cargo_name": "Steel Pipes",
            "cargo_weight": 20.0,
            "total_weight": 28.5,
            "total_size_arr_str": "13,2.5,4"
        },
        "transport_plan": {
            "start_point": "Beijing",
            "end_point": "Shanghai",
            # Use ISO format strings for datetime
            "start_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_date": (datetime.now() + timedelta(days=2)).isoformat()
        }
    }
    
    print("\n[POST] Creating Application...")
    response = requests.post(BASE_URL + "/", json=payload)
    
    if response.status_code != 201:
        print(f"FAILED: {response.status_code}")
        print(response.text)
        return
        
    data = response.json()
    app_id = data["id"]
    print(f"SUCCESS: Created Application ID: {app_id}")
    print(f"Vehicle: {data.get('vehicle_info', {}).get('tractor_plate_number')}")
    print(f"Axis Weights: {data.get('vehicle_info', {}).get('axis_weights')}")
    
    # 2. Get Application
    print(f"\n[GET] Retrieving Application {app_id}...")
    response = requests.get(f"{BASE_URL}/{app_id}")
    
    if response.status_code != 200:
        print(f"FAILED: {response.status_code}")
        return
        
    data = response.json()
    print(f"SUCCESS: Retrieved Application")
    print(f"Status: {data['status']}")
    print(f"Driver: {data['owner_info']['driver_name']}")
    
    # 3. Update Application
    print(f"\n[PUT] Updating Application {app_id}...")
    update_payload = {
        "status": "SUBMITTED",
        "cargo_info": {
            "cargo_name": "Updated Steel Pipes",
            "cargo_weight": 22.0
        }
    }
    
    response = requests.put(f"{BASE_URL}/{app_id}", json=update_payload)
    
    if response.status_code != 200:
        print(f"FAILED: {response.status_code}")
        return
        
    data = response.json()
    print(f"SUCCESS: Updated Application")
    print(f"New Status: {data['status']}")
    print(f"New Cargo Name: {data['cargo_info']['cargo_name']}")
    
    # 4. List Applications
    print(f"\n[GET] Listing Applications...")
    response = requests.get(BASE_URL + "/")
    
    if response.status_code != 200:
        print(f"FAILED: {response.status_code}")
        return
        
    apps = response.json()
    print(f"SUCCESS: Found {len(apps)} applications")
    
    # 5. Delete Application
    print(f"\n[DELETE] Deleting Application {app_id}...")
    response = requests.delete(f"{BASE_URL}/{app_id}")
    
    if response.status_code != 204:
        print(f"FAILED: {response.status_code}")
        return
        
    print("SUCCESS: Deleted Application")
    
    # Verify Deletion
    response = requests.get(f"{BASE_URL}/{app_id}")
    if response.status_code == 404:
        print("VERIFIED: Application not found after deletion")
    else:
        print(f"WARNING: Application still exists or other error: {response.status_code}")

if __name__ == "__main__":
    try:
        test_application_workflow()
    except Exception as e:
        print(f"An error occurred: {e}")
