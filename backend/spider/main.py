"""
Spider orchestrator - runs the full crawl → process → upload pipeline.

Usage:
    python -m backend.spider.main              # Run once
    python -m backend.spider.main --schedule   # Run with APScheduler (every 30 min)

The pipeline:
    1. Crawl fjetc.com API for traffic events + road construction (→ JSON)
    2. Process JSON into structured Markdown files (→ road_details/)
    3. Upload new Markdown files to MaxKB knowledge base
"""
import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.spider.config import SpiderConfig
from backend.spider.crawler import FJETCCrawler
from backend.spider.processor import EventProcessor
from backend.spider.maxkb_uploader import MaxKBUploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('spider')


class SpiderPipeline:
    """Orchestrates the full crawl → process → upload pipeline."""

    def __init__(self):
        self.crawler = FJETCCrawler()
        self.processor = EventProcessor()
        self.uploader = MaxKBUploader()

    def run(self, skip_upload: bool = False) -> dict:
        """
        Execute the full pipeline.

        Returns:
            Dict with stats for each stage.
        """
        start_time = time.time()
        result = {
            "started_at": datetime.now().isoformat(),
            "crawl": {},
            "process": {},
            "upload": {},
            "success": True,
        }

        # ---- Stage 1: Crawl ----
        logger.info("=" * 50)
        logger.info("STAGE 1: Crawling fjetc.com API")
        logger.info("=" * 50)
        try:
            SpiderConfig.ensure_dirs()
            incidents, constructions = self.crawler.crawl_all()
            result["crawl"] = {
                "incidents": len(incidents),
                "constructions": len(constructions),
            }
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            result["success"] = False
            result["error"] = f"Crawl: {e}"
            return result

        # ---- Stage 2: Process JSON → Markdown ----
        logger.info("=" * 50)
        logger.info("STAGE 2: Processing JSON to Markdown")
        logger.info("=" * 50)
        try:
            proc_stats = self.processor.process_all()
            result["process"] = {
                k: v for k, v in proc_stats.items()
            }
            total_processed = sum(v["processed"] for v in proc_stats.values())
            logger.info(f"Total new files: {total_processed}")
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            result["success"] = False
            result["error"] = f"Process: {e}"
            return result

        # ---- Stage 3: Upload to MaxKB ----
        if skip_upload:
            logger.info("STAGE 3: Skipped (--skip-upload)")
            result["upload"] = {"skipped": True}
        else:
            logger.info("=" * 50)
            logger.info("STAGE 3: Uploading to MaxKB")
            logger.info("=" * 50)
            try:
                upload_stats = self.uploader.upload_folder()
                result["upload"] = upload_stats
            except Exception as e:
                logger.error(f"Upload failed: {e}")
                result["success"] = False
                result["error"] = f"Upload: {e}"

        elapsed = time.time() - start_time
        result["elapsed_seconds"] = round(elapsed, 2)
        result["finished_at"] = datetime.now().isoformat()

        logger.info(f"Pipeline complete in {elapsed:.1f}s")
        return result


def run_once(skip_upload: bool = False) -> dict:
    """Run the pipeline once."""
    pipeline = SpiderPipeline()
    return pipeline.run(skip_upload=skip_upload)


def run_scheduled(interval_minutes: int = 30):
    """
    Run the pipeline on a schedule using APScheduler.
    Install with: pip install apscheduler
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    pipeline = SpiderPipeline()

    def job():
        logger.info("=== Scheduled spider run ===")
        result = pipeline.run()
        if result["success"]:
            logger.info(
                f"Scheduled run OK: crawl={result['crawl']}, "
                f"process={result['process']}, upload={result['upload']}"
            )
        else:
            logger.error(f"Scheduled run FAILED: {result.get('error')}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(job, 'interval', minutes=interval_minutes, id='spider')
    scheduler.start()

    logger.info(f"Spider scheduler started (every {interval_minutes} min). Press Ctrl+C to exit.")

    # Run once immediately
    job()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped.")
        scheduler.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Spider: crawl traffic data → MaxKB")
    parser.add_argument(
        "--schedule", "-s",
        action="store_true",
        help="Run on a schedule (every 30 min) instead of once",
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=30,
        help="Schedule interval in minutes (default: 30)",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip uploading to MaxKB (crawl + process only)",
    )
    parser.add_argument(
        "--crawl-only",
        action="store_true",
        help="Only crawl, skip processing and upload",
    )

    args = parser.parse_args()

    # Validate config
    missing = SpiderConfig.validate()
    if missing and not args.skip_upload and not args.crawl_only:
        logger.warning(f"Missing config: {missing}. Upload may fail.")

    if args.crawl_only:
        logger.info("=== Crawl only mode ===")
        SpiderConfig.ensure_dirs()
        crawler = FJETCCrawler()
        crawler.crawl_all()
    elif args.schedule:
        run_scheduled(interval_minutes=args.interval)
    else:
        result = run_once(skip_upload=args.skip_upload)
        print("\n" + "=" * 50)
        print("Pipeline Result:")
        print(f"  Crawl:    {result['crawl']}")
        print(f"  Process:  {result['process']}")
        print(f"  Upload:   {result['upload']}")
        print(f"  Elapsed:  {result['elapsed_seconds']}s")
        print(f"  Success:  {result['success']}")
        print("=" * 50)


if __name__ == "__main__":
    main()
