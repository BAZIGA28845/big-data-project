import json
import logging
from datetime import datetime, timezone

import pandas as pd
import psycopg2.extras

from db import get_connection

logger = logging.getLogger(__name__)


def create_tables():
    """
    Creates the raw and cleaned tables if they don't already exist.
    Safe to call every run.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS raw_gdacs (
        id SERIAL PRIMARY KEY,
        fetched_at TIMESTAMPTZ NOT NULL,
        payload JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS clean_gdacs (
        event_id INTEGER PRIMARY KEY,
        event_type TEXT NOT NULL,
        event_name TEXT,
        alert_level TEXT NOT NULL,
        alert_score DOUBLE PRECISION,
        country TEXT,
        iso3 TEXT,
        from_date TIMESTAMP,
        to_date TIMESTAMP,
        year INTEGER NOT NULL,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        severity_value DOUBLE PRECISION,
        severity_unit TEXT,
        loaded_at TIMESTAMPTZ NOT NULL
    );
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()
        logger.info("Tables verified/created: raw_gdacs, clean_gdacs")
    except psycopg2.Error as e:
        logger.error(f"Failed to create tables (target table may be locked): {e}")
        raise RuntimeError("Could not create/verify tables") from e


def load_raw(raw_payload: dict):
    """Inserts the untouched API response as a JSONB row."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO raw_gdacs (fetched_at, payload) VALUES (%s, %s)",
                    (datetime.now(timezone.utc), json.dumps(raw_payload)),
                )
            conn.commit()
        logger.info("Raw payload inserted into raw_gdacs")
    except psycopg2.Error as e:
        logger.error(f"Failed to insert raw payload: {e}")
        raise RuntimeError("Raw load failed") from e


def get_latest_loaded_year():
    """
    Returns the most recent year already present in clean_gdacs,
    or None if the table is empty. Used to drive incremental loading.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(year) FROM clean_gdacs")
                result = cur.fetchone()[0]
        return result
    except psycopg2.Error as e:
        logger.error(f"Failed to read latest loaded year: {e}")
        raise RuntimeError("Could not check existing data for incremental load") from e


def load_clean(df: pd.DataFrame):
    """
    Upserts cleaned rows into clean_gdacs. Safe to re-run: rows with
    the same event_id are updated in place rather than duplicated,
    thanks to the PRIMARY KEY + ON CONFLICT clause.
    """
    if df.empty:
        logger.warning("load_clean received an empty DataFrame - nothing to load")
        return

    def clean_text(value):
        """Converts pandas NaN, empty, or whitespace-only strings to proper None."""
        if pd.isna(value):
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    now = datetime.now(timezone.utc)
    rows = [
        (
            int(r.event_id), r.event_type, clean_text(r.event_name), r.alert_level,
            None if pd.isna(r.alert_score) else float(r.alert_score),
            clean_text(r.country), clean_text(r.iso3),
            r.from_date.to_pydatetime(), r.to_date.to_pydatetime(),
            int(r.year),
            None if pd.isna(r.latitude) else float(r.latitude),
            None if pd.isna(r.longitude) else float(r.longitude),
            None if pd.isna(r.severity_value) else float(r.severity_value),
            clean_text(r.severity_unit),
            now,
        )
        for r in df.itertuples(index=False)
    ]

    upsert_sql = """
        INSERT INTO clean_gdacs (
            event_id, event_type, event_name, alert_level, alert_score,
            country, iso3, from_date, to_date, year, latitude, longitude,
            severity_value, severity_unit, loaded_at
        )
        VALUES %s
        ON CONFLICT (event_id)
        DO UPDATE SET
            event_type = EXCLUDED.event_type,
            event_name = EXCLUDED.event_name,
            alert_level = EXCLUDED.alert_level,
            alert_score = EXCLUDED.alert_score,
            country = EXCLUDED.country,
            iso3 = EXCLUDED.iso3,
            from_date = EXCLUDED.from_date,
            to_date = EXCLUDED.to_date,
            year = EXCLUDED.year,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            severity_value = EXCLUDED.severity_value,
            severity_unit = EXCLUDED.severity_unit,
            loaded_at = EXCLUDED.loaded_at
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(cur, upsert_sql, rows)
            conn.commit()
        logger.info(f"Upserted {len(rows)} rows into clean_gdacs")
    except psycopg2.Error as e:
        logger.error(f"Failed to load cleaned data (table may be locked): {e}")
        raise RuntimeError("Clean load failed") from e