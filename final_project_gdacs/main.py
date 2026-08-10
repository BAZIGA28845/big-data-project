import logging
import sys
from pathlib import Path

from extract import get_raw_data
from transform import clean_data
from validate import validate_data
from load import create_tables, load_raw, load_clean, get_latest_loaded_year

LOG_FILE = Path("logs") / "pipeline.log"


def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def run_pipeline(force_refresh: bool = False):
    logger = logging.getLogger("main")
    logger.info("=== GDACS pipeline run started ===")

    try:
        create_tables()

        latest_year = get_latest_loaded_year()
        if latest_year is None:
            logger.info("No existing data found - this will be a full initial load")
        else:
            logger.info(f"Existing data found up to year {latest_year} - loading only newer years")

        raw_payload = get_raw_data(force_refresh=force_refresh)

        # Always store the raw pull, regardless of what's incremental
        load_raw(raw_payload)

        df = clean_data(raw_payload)
        df = validate_data(df)

        if df.empty:
            logger.warning("No valid rows to load after cleaning/validation - stopping")
            return

        if latest_year is not None:
            before = len(df)
            df = df[df["year"] > latest_year]
            logger.info(f"Incremental filter: {before} rows -> {len(df)} rows (years > {latest_year})")

        if df.empty:
            logger.info("No new years to load - database is already up to date")
            return

        load_clean(df)

        logger.info(f"=== Pipeline run completed successfully: {len(df)} rows loaded/updated ===")

    except RuntimeError as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    force = "--refresh" in sys.argv
    run_pipeline(force_refresh=force)