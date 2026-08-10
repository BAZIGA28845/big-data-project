import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _extract_row(feature: dict) -> dict:
    """
    Flattens one GDACS GeoJSON feature into a flat dict.
    Note: population is NOT extracted - confirmed by inspecting the raw
    data that GDACS's SEARCH/list endpoint never includes population
    exposure data for any event type; it's a known limitation of this
    endpoint, not a bug. iso3 is captured as a clean country code
    (better for Tableau map matching than the free-text 'country' field,
    which has inconsistent spacing/formatting across events).
    """
    props = feature.get("properties", {}) or {}
    geometry = feature.get("geometry", {}) or {}
    coords = geometry.get("coordinates", [None, None])
    longitude, latitude = (coords[0], coords[1]) if len(coords) >= 2 else (None, None)

    severity = props.get("severitydata") or {}

    return {
        "event_id": props.get("eventid"),
        "episode_id": props.get("episodeid"),
        "event_type": props.get("eventtype"),
        "event_name": props.get("eventname"),
        "alert_level": props.get("alertlevel"),
        "alert_score": props.get("alertscore"),
        "country": props.get("country"),
        "iso3": props.get("iso3"),
        "from_date": props.get("fromdate"),
        "to_date": props.get("todate"),
        "latitude": latitude,
        "longitude": longitude,
        "severity_value": severity.get("severity"),
        "severity_unit": severity.get("severityunit"),
    }


def clean_data(raw_payload: dict) -> pd.DataFrame:
    """
    Takes the raw GDACS payload (a dict with a 'features' list) and
    returns a cleaned, deduplicated pandas DataFrame ready for loading.
    """
    features = raw_payload.get("features", [])

    if not features:
        logger.warning("No features in raw payload; returning empty cleaned DataFrame")
        return pd.DataFrame(columns=[
            "event_id", "event_type", "event_name", "alert_level", "alert_score",
            "country", "iso3", "from_date", "to_date", "year", "latitude", "longitude",
            "severity_value", "severity_unit",
        ])

    rows = [_extract_row(f) for f in features]
    df = pd.DataFrame(rows)

    before = len(df)
    df = df.dropna(subset=["event_id", "event_type", "alert_level"])
    logger.info(f"Dropped {before - len(df)} rows missing event_id/event_type/alert_level")

    df["event_id"] = pd.to_numeric(df["event_id"], errors="coerce")
    df["episode_id"] = pd.to_numeric(df["episode_id"], errors="coerce").fillna(0)
    df["alert_score"] = pd.to_numeric(df["alert_score"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["severity_value"] = pd.to_numeric(df["severity_value"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["event_id"])
    logger.info(f"Dropped {before - len(df)} rows with non-numeric event_id")
    df["event_id"] = df["event_id"].astype(int)

    df["from_date"] = pd.to_datetime(df["from_date"], errors="coerce")
    df["to_date"] = pd.to_datetime(df["to_date"], errors="coerce")
    df["year"] = df["from_date"].dt.year

    before = len(df)
    df = df.dropna(subset=["from_date", "year"])
    logger.info(f"Dropped {before - len(df)} rows with unparseable dates")
    df["year"] = df["year"].astype(int)

    before = len(df)
    df = df.sort_values("episode_id").drop_duplicates(subset="event_id", keep="last")
    logger.info(f"Dropped {before - len(df)} duplicate episode rows (kept latest episode per event)")

    df["alert_level"] = df["alert_level"].astype(str).str.strip().str.capitalize()

    # Trim whitespace from country names so "China " and "China" aren't
    # treated as two different values downstream (Tableau, SQL grouping)
    df["country"] = df["country"].str.strip()

    # Convert pandas' NaN markers back to proper None for text columns,
    # so missing values are stored as real NULLs in Postgres instead of
    # the literal string "NaN"
    text_columns = ["event_name", "country", "iso3", "severity_unit"]
    for col in text_columns:
        df[col] = df[col].where(df[col].notna(), None)
        df[col] = df[col].replace("", None)  # empty strings also become NULL

    df = df.reset_index(drop=True)
    logger.info(f"Transform complete: {len(df)} clean rows ready for loading")
    return df