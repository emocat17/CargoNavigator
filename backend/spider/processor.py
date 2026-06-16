"""
Process JSON event data into structured Markdown files.
Extracts: highway name, direction, stake range, duration, latest progress, publish time.
"""
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

from .config import SpiderConfig
from .file_manager import FileManager

logger = logging.getLogger(__name__)


def extract_direction_from_remark(remark: str) -> str:
    """Try to extract direction info from the remark field."""
    if not remark:
        return ""
    match = re.search(r'([一-龥]+往[一-龥]+方向)', remark)
    return match.group(1) if match else ""


def process_event(event: dict) -> dict:
    """
    Map a raw API event to a structured dict for Markdown generation.

    Fields extracted:
      - url: detail page URL
      - highway_name: highway name (title)
      - direction: traffic direction
      - stake_number: start-end stake range
      - duration: occurrence time range
      - latest_progress: latest update from the event track
      - publish_time: publish timestamp
    """
    highway = event.get("title", "未知高速")

    direction = event.get("directionname", "")
    if not direction:
        direction = extract_direction_from_remark(event.get("remark", ""))
    if not direction:
        direction = "未知方向"

    start_stake = event.get("startstake", "")
    end_stake = event.get("endstake", "")
    stake = f"{start_stake}-{end_stake}" if start_stake and end_stake else (start_stake or end_stake or "未知桩号")

    occtime = event.get("occtime", "")
    planover = event.get("planovertime")
    duration = str(occtime)
    if planover:
        duration += f" 至 {planover}"
    else:
        duration += " (预计结束时间未知)"

    # Latest progress from the track timeline
    latest_progress = ""
    tracks = event.get("track", [])
    if tracks:
        for track in reversed(tracks):
            if track.get("content"):
                latest_progress = track["content"]
                break
    if not latest_progress:
        latest_progress = event.get("remark", "暂无详情")

    publish_time = event.get("occtime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    event_id = event.get("eventid", "")
    url = f"https://www.fjetc.com/traffic-info/{event_id}"

    return {
        "url": url,
        "highway_name": highway,
        "direction": direction,
        "stake_number": stake,
        "duration": duration,
        "latest_progress": latest_progress,
        "publish_time": publish_time,
        "extract_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "raw_data": event,
    }


def generate_filename(data: dict) -> Optional[str]:
    """
    Generate a filename from publish_time + highway_name + stake_number.
    Returns None if key fields are unknown.
    """
    highway = data.get('highway_name', '未知高速')
    stake = data.get('stake_number', '未知桩号')

    if "未知" in highway and "未知" in stake:
        return None

    publish_time = data.get('publish_time', '')
    if not publish_time:
        return None

    date_part = publish_time.replace(' ', '_').replace(':', '-')
    highway_clean = re.sub(r'[^\w一-鿿]', '_', highway)
    stake_clean = re.sub(r'[^\w一-鿿]', '_', stake)

    return f"{date_part}_{highway_clean}_{stake_clean}.md"


def save_to_markdown(data: dict, filepath: Path):
    """Write extracted event data as a Markdown file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("# 福建高速交通事件详情\n\n")
        f.write(f"**URL**: {data['url']}\n\n")
        f.write(f"**发布时间**: {data['publish_time']}\n\n")
        f.write(f"**提取时间**: {data['extract_time']}\n\n")
        f.write(f"## 高速名称\n\n{data['highway_name']}\n\n")
        f.write(f"## 方向\n\n{data['direction']}\n\n")
        f.write(f"## 桩号区间\n\n{data['stake_number']}\n\n")
        f.write(f"## 持续时间\n\n{data['duration']}\n\n")
        f.write(f"## 最新进度\n\n{data['latest_progress']}\n")
    logger.debug(f"Saved: {filepath}")


class EventProcessor:
    """Process JSON event data into Markdown files."""

    def __init__(self):
        cfg = SpiderConfig
        self.json_dir = cfg.JSON_DIR
        self.output_dir = cfg.OUTPUT_DIR
        self.file_mgr = FileManager(cfg.UPLOADED_RECORD)

    def process_json(self, json_filename: str) -> tuple:
        """
        Process a single JSON file from the crawler.

        Args:
            json_filename: e.g. 'Traffic_incident_code.json' or 'Road_construction_code.json'.

        Returns:
            (processed_count, skipped_count, filtered_count)
        """
        json_path = self.json_dir / json_filename
        if not json_path.exists():
            logger.error(f"JSON file not found: {json_path}")
            return 0, 0, 0

        # Determine sub-directory
        if "traffic" in json_filename.lower():
            sub_dir = self.output_dir / "traffic_incident_details"
            category = "交通事件"
        else:
            sub_dir = self.output_dir / "road_construction_details"
            category = "道路施工"

        sub_dir.mkdir(parents=True, exist_ok=True)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        events = data.get('events_data', [])
        if not events:
            logger.warning(f"No events_data found in {json_filename}")
            return 0, 0, 0

        uploaded: Set[str] = self.file_mgr.get_uploaded()

        processed = 0
        skipped = 0
        filtered = 0

        for event in events:
            try:
                processed_data = process_event(event)
                filename = generate_filename(processed_data)

                if filename is None:
                    filtered += 1
                    continue

                filepath = sub_dir / filename

                # Skip if already exists locally or already uploaded
                if filepath.exists():
                    skipped += 1
                    continue
                if filename in uploaded:
                    skipped += 1
                    continue

                save_to_markdown(processed_data, filepath)
                processed += 1

            except Exception as e:
                logger.error(f"Error processing event: {e}")

        logger.info(
            f"{category} done: processed={processed}, skipped={skipped}, filtered={filtered}"
        )
        return processed, skipped, filtered

    def process_all(self) -> dict:
        """Process all crawler JSON files. Returns stats dict."""
        SpiderConfig.ensure_dirs()
        results = {}

        for json_file in ["Traffic_incident_code.json", "Road_construction_code.json"]:
            p, s, f = self.process_json(json_file)
            results[json_file] = {"processed": p, "skipped": s, "filtered": f}

        return results
