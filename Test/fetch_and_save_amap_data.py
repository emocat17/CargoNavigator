
import requests
import json
import os

API_KEY = "61ded56e661c7338f95ccafd0c4642d5"
BASE_URL = "https://restapi.amap.com"

def get_geo_code(address):
    url = f"{BASE_URL}/v3/geocode/geo"
    params = {
        "address": address,
        "key": API_KEY,
        "output": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("status") == "1" and int(data.get("count", 0)) > 0:
        return data["geocodes"][0]["location"]
    else:
        print(f"Geocode failed for {address}: {data}")
        return None

def plan_route(origin, destination):
    url = f"{BASE_URL}/v3/direction/driving"
    params = {
        "origin": origin,
        "destination": destination,
        "strategy": 0, # 0: 速度优先 (Speed priority)
        "key": API_KEY,
        "output": "json",
        "extensions": "all"
    }
    response = requests.get(url, params=params)
    return response.json()

def main():
    origin_addr = "福建省三明厦钨新能源"
    dest_addr = "福建省平潭跨境电商园"
    
    print(f"Geocoding {origin_addr}...")
    origin_loc = get_geo_code(origin_addr)
    print(f"Origin Location: {origin_loc}")
    
    print(f"Geocoding {dest_addr}...")
    dest_loc = get_geo_code(dest_addr)
    print(f"Destination Location: {dest_loc}")
    
    if origin_loc and dest_loc:
        print("Planning route...")
        data = plan_route(origin_loc, dest_loc)
        
        output_dir = r"d:\GitWorks\CargoNavigator\docs\SmartRoute"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "amap_response_sample.json")
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"Full response saved to {output_file}")
    else:
        print("Could not get coordinates.")

if __name__ == "__main__":
    main()
