"""
FJETC.com API crawler - fetches Fujian Expressway traffic events and road construction data.
Uses AES-CBC encryption for API communication.

The API returns full event details in JSON, so we don't need to scrape individual pages.
"""
import json
import time
import hashlib
import binascii
import logging
from pathlib import Path
from typing import Optional

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from .config import SpiderConfig

logger = logging.getLogger(__name__)


class FJETCCrawler:
    """
    Crawler for fjetc.com traffic API.
    Handles AES encryption/decryption of API requests/responses.
    """

    TYPE_INCIDENT = "1006001"      # Traffic incidents (交通事件)
    TYPE_CONSTRUCTION = "1006002"  # Road construction (道路施工)

    def __init__(self):
        cfg = SpiderConfig
        self.public_key = cfg.FJETC_PUBLIC_KEY
        self.api_url = cfg.FJETC_API_URL
        self.key = self.public_key.encode('utf-8')
        self.iv = self.public_key[:16].encode('utf-8')
        self.timeout = cfg.REQUEST_TIMEOUT
        self.page_size = cfg.PAGE_SIZE
        self.max_pages = cfg.MAX_PAGES
        self.delay = cfg.REQUEST_DELAY

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/143.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://www.fjetc.com/traffic-info",
            "Origin": "https://www.fjetc.com",
        })

    # ---- AES Helpers ----

    def _encrypt(self, data_str: str) -> str:
        data_bytes = data_str.encode('utf-8')
        padded = pad(data_bytes, AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return binascii.hexlify(cipher.encrypt(padded)).decode('utf-8').upper()

    def _decrypt(self, hex_data: str) -> str:
        ciphertext = binascii.unhexlify(hex_data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')

    # ---- API Calls ----

    def fetch_page(self, type_code: str, page: int = 1, size: Optional[int] = None) -> list:
        """
        Fetch a single page of events.

        Args:
            type_code: '1006001' for incidents, '1006002' for construction.
            page: Page number.
            size: Items per page (defaults to config PAGE_SIZE).

        Returns:
            List of event dicts from the API response.
        """
        if size is None:
            size = self.page_size

        data = {
            "all": 1,
            "city": "",
            "loadAllEvent": False,
            "loadBydDistance": False,
            "page": page,
            "roadid": "",
            "size": size,
            "type": type_code,
        }

        timestamp = int(time.time() * 1000)
        data_json = json.dumps(data, separators=(',', ':'))
        sign_str = data_json + str(timestamp)
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

        payload_obj = {"data": data, "timestamp": timestamp, "sign": sign}
        payload_json = json.dumps(payload_obj, separators=(',', ':'))
        encrypted_payload = self._encrypt(payload_json)

        try:
            logger.info(f"Fetching events type={type_code}, page={page}, size={size}")
            resp = self.session.post(self.api_url, data=encrypted_payload, timeout=self.timeout)
            resp.raise_for_status()

            decrypted = self._decrypt(resp.text)
            resp_json = json.loads(decrypted)

            if resp_json.get("code") != "200":
                logger.error(f"API error code: {resp_json.get('code')}, msg: {resp_json.get('msg')}")
                return []

            return resp_json.get("data", [])

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

    def fetch_all(self, type_code: str) -> list:
        """
        Fetch all events of a given type by paginating through all pages.

        Returns:
            Deduplicated list of all event dicts.
        """
        all_events = []
        seen_ids = set()

        for page in range(1, self.max_pages + 1):
            events = self.fetch_page(type_code, page)

            if not events:
                break

            new_count = 0
            for event in events:
                event_id = event.get('eventid')
                if event_id and event_id not in seen_ids:
                    seen_ids.add(event_id)
                    all_events.append(event)
                    new_count += 1

            logger.info(f"Page {page}: received {len(events)}, new {new_count}, total {len(all_events)}")

            if new_count == 0 or len(events) < self.page_size:
                break

            time.sleep(self.delay)

        logger.info(f"Total unique events for type={type_code}: {len(all_events)}")
        return all_events

    def save_events(self, events: list, title: str, filename: str) -> Path:
        """
        Save events to a JSON file.

        Returns:
            Path to the saved JSON file.
        """
        event_codes = []
        event_urls = []
        unique_events = []
        seen = set()

        for event in events:
            code = event.get("eventid")
            if code and code not in seen:
                seen.add(code)
                event_codes.append(code)
                event_urls.append(f"https://www.fjetc.com/traffic-info/{code}")
                unique_events.append(event)

        output = {
            "title": title,
            "update_time": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_count": len(event_urls),
            "event_urls": event_urls,
            "event_codes": event_codes,
            "events_data": unique_events,
        }

        json_dir = SpiderConfig.JSON_DIR
        json_dir.mkdir(parents=True, exist_ok=True)
        filepath = json_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)

        logger.info(f"Saved {len(unique_events)} events to {filepath}")
        return filepath

    def crawl_all(self):
        """
        Main crawl method: fetch both incidents and construction data, save to JSON.
        """
        SpiderConfig.ensure_dirs()

        logger.info("=== Step 1: Fetching Traffic Incidents ===")
        incidents = self.fetch_all(self.TYPE_INCIDENT)
        self.save_events(incidents, "福建高速交通事件链接列表", "Traffic_incident_code.json")

        time.sleep(1)

        logger.info("=== Step 2: Fetching Road Construction ===")
        constructions = self.fetch_all(self.TYPE_CONSTRUCTION)
        self.save_events(constructions, "福建高速道路施工链接列表", "Road_construction_code.json")

        return incidents, constructions
