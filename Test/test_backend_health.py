import httpx
import sys

def test_backend_health():
    url = "http://localhost:8000/health"
    print(f"Testing backend health at {url}...")
    try:
        response = httpx.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Backend Health Check Passed!")
        else:
            print("❌ Backend Health Check Failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_backend_health()
