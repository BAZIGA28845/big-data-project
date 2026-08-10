import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
FROM_DATE = "2000-01-01"
TO_DATE = "2024-12-31"
RAW_DATA_PATH = Path("data") / "gdacs_raw.json"

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1
PAGE_SIZE = 100  # GDACS's own max per request


def fetch_one_page(from_date: str, to_date: str, page_number: int) -> dict:
    """
    Fetches a single page of GDACS results, retrying with exponential
    backoff (1s, 2s, 4s...) if the request fails.
    """
    params = {
        "fromDate": from_date,
        "toDate": to_date,
        "alertlevel": "orange;red",  # scoped to moderate/severe events only - Green excluded on purpose
        "pagenumber": page_number,
        "pagesize": PAGE_SIZE,
    }
    delay = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Requesting page {page_number} (attempt {attempt}/{MAX_RETRIES})")
            response = requests.get(BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            return response.json()

        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Page {page_number}, attempt {attempt} failed: {e}")
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Failed to fetch page {page_number} after {MAX_RETRIES} attempts"
                ) from e
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2


def fetch_from_api(from_date: str = FROM_DATE, to_date: str = TO_DATE) -> dict:
    """
    Fetches ALL GDACS events (Orange/Red only) in the date range by
    looping through pages (the API caps each response at 100 records).
    Stops once a page comes back with fewer than PAGE_SIZE records,
    meaning we've reached the end. Returns a single combined payload
    with all features merged together.
    """
    all_features = []
    page_number = 1

    while True:
        payload = fetch_one_page(from_date, to_date, page_number)
        features = payload.get("features", [])

        if not features:
            logger.info(f"Page {page_number} returned no events - stopping")
            break

        all_features.extend(features)
        logger.info(f"Page {page_number}: {len(features)} events (running total: {len(all_features)})")

        if len(features) < PAGE_SIZE:
            # This was the last (partial) page
            break

        page_number += 1
        time.sleep(0.3)  # small pause between pages, be polite to the API

    if not all_features:
        logger.warning(f"No events found at all for {from_date} to {to_date}")

    return {"type": "FeatureCollection", "features": all_features}


def get_raw_data(force_refresh: bool = False) -> dict:
    """
    Returns the raw GDACS payload (all pages combined). Uses a local
    cached copy if one already exists, so re-running the pipeline
    doesn't re-download data that was already fetched successfully.
    """
    RAW_DATA_PATH.parent.mkdir(exist_ok=True)

    if RAW_DATA_PATH.exists() and not force_refresh:
        logger.info(f"Found cached raw data at {RAW_DATA_PATH}, skipping API call")
        with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    payload = fetch_from_api()

    with open(RAW_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    logger.info(f"Saved raw data to {RAW_DATA_PATH}")

    return payload