
import requests
import json
import time
import hashlib
import binascii
import os
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

class FJEtcAPI:
    """
    Handles API interactions with fjetc.com, including encryption/decryption.
    """
    PUBLIC_KEY = "f1ed4UgYNLWSXtR0kHKZcqFFhyakX6WH"
    URL = "https://www.fjetc.com/mgsfwq/FunctionList/Traffic/getTrafficMessage"
    
    def __init__(self):
        self.key = self.PUBLIC_KEY.encode('utf-8')
        self.iv = self.PUBLIC_KEY[:16].encode('utf-8')
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.fjetc.com/traffic-info",
            "Origin": "https://www.fjetc.com"
        })

    def _encrypt(self, data_str):
        try:
            data_bytes = data_str.encode('utf-8')
            padded_data = pad(data_bytes, AES.block_size)
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            ciphertext = cipher.encrypt(padded_data)
            return binascii.hexlify(ciphertext).decode('utf-8').upper()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def _decrypt(self, hex_data):
        try:
            ciphertext = binascii.unhexlify(hex_data)
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            decrypted_padded = cipher.decrypt(ciphertext)
            decrypted = unpad(decrypted_padded, AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    def get_events_page(self, type_code, page=1, size=10):
        """
        Fetch a single page of events.
        """
        data = {
            "all": 1,
            "city": "",
            "loadAllEvent": False,
            "loadBydDistance": False,
            "page": page,
            "roadid": "",
            "size": size,
            "type": type_code
        }
        
        timestamp = int(time.time() * 1000)
        data_json = json.dumps(data, separators=(',', ':'))
        
        sign_str = data_json + str(timestamp)
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        
        payload_obj = {
            "data": data,
            "timestamp": timestamp,
            "sign": sign
        }
        payload_json = json.dumps(payload_obj, separators=(',', ':'))
        encrypted_payload = self._encrypt(payload_json)
        
        try:
            logger.info(f"Requesting events type={type_code}, page={page}, size={size}")
            response = self.session.post(self.URL, data=encrypted_payload, timeout=30)
            response.raise_for_status()
            
            decrypted_resp = self._decrypt(response.text)
            resp_json = json.loads(decrypted_resp)
            
            if resp_json.get("code") != "200":
                logger.error(f"API returned error code: {resp_json.get('code')}")
                return []
                
            return resp_json.get("data", [])
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []

    def get_all_events(self, type_code):
        """
        Fetch all events by paginating.
        """
        all_events = []
        page = 1
        size = 500 
        seen_ids = set()
        max_pages = 300 # Safety limit
        
        while page <= max_pages:
            events = self.get_events_page(type_code, page, size)
            if not events:
                break
            
            # Check for duplicates in the current page
            new_events_count = 0
            for event in events:
                event_id = event.get('eventid')
                if event_id and event_id not in seen_ids:
                    seen_ids.add(event_id)
                    all_events.append(event)
                    new_events_count += 1
            
            logger.info(f"Page {page}: Fetched {len(events)} events, {new_events_count} new.")
            
            if new_events_count == 0:
                logger.info("No new events found in this page. Stopping pagination.")
                break
                
            if len(events) < size:
                # If we got fewer items than requested, it's likely the last page
                break
                
            page += 1
            time.sleep(0.5) # Be nice to the server
            
        return all_events

def save_to_json(events, title, filename):
    """
    Save events to JSON file in the required format.
    """
    event_codes = []
    event_urls = []
    
    for event in events:
        code = event.get("eventid")
        if code:
            event_codes.append(code)
            event_urls.append(f"https://www.fjetc.com/traffic-info/{code}")
    
    # Remove duplicates
    unique_codes = []
    unique_urls = []
    unique_events = []
    seen = set()
    for i, code in enumerate(event_codes):
        if code not in seen:
            seen.add(code)
            unique_codes.append(code)
            unique_urls.append(event_urls[i])
            unique_events.append(events[i])
            
    output_data = {
        "title": title,
        "update_time": time.strftime('%Y-%m-%d %H:%M:%S'),
        "total_count": len(unique_urls),
        "event_urls": unique_urls,
        "event_codes": unique_codes,
        "events_data": unique_events
    }
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'json')
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, filename)
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved {len(unique_urls)} events to {json_path}")
    except Exception as e:
        logger.error(f"Failed to save JSON: {e}")

def main():
    api = FJEtcAPI()
    
    # 1. Traffic Incidents
    logger.info("Fetching Traffic Incidents...")
    incidents = api.get_all_events("1006001")
    save_to_json(incidents, "福建高速交通事件链接列表", "Traffic_incident_code.json")
    
    # Wait a bit
    time.sleep(1)
    
    # 2. Road Construction
    logger.info("Fetching Road Construction...")
    constructions = api.get_all_events("1006002")
    save_to_json(constructions, "福建高速道路施工链接列表", "Road_construction_code.json")

if __name__ == "__main__":
    main()
