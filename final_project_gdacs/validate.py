import logging

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["event_id", "event_type", "alert_level", "year", "latitude", "longitude"]

MIN_LATITUDE, MAX_LATITUDE = -90, 90
MIN_LONGITUDE, MAX_LONGITUDE = -180, 180
MIN_YEAR, MAX_YEAR = 2000, 2024
MIN_ALERT_SCORE, MAX_ALERT_SCORE = 0, 10  # generous upper bound to catch clear data errors


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Runs explicit data-quality checks on the cleaned GDACS DataFrame.
    Rows that fail validation are dropped and logged as warnings,
    rather than silently loaded or left to the database to reject.
    Returns a DataFrame containing only rows that passed every check.
    """
    if df.empty:
        logger.warning("validate_data received an empty DataFrame")
        return df

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df = df.copy()
    original_count = len(df)

    # --- Check 1: missing/null values in important columns ---
    missing_mask = df[REQUIRED_COLUMNS].isna().any(axis=1)
    if missing_mask.any():
        logger.warning(f"Flagging {missing_mask.sum()} rows with missing required values")
    df = df[~missing_mask]

    # --- Check 2: unexpected data types ---
    bad_type_mask = ~df["year"].apply(lambda v: isinstance(v, (int,)))
    bad_type_mask |= ~df["latitude"].apply(lambda v: isinstance(v, (int, float)))
    bad_type_mask |= ~df["longitude"].apply(lambda v: isinstance(v, (int, float)))
    if bad_type_mask.any():
        logger.warning(f"Flagging {bad_type_mask.sum()} rows with unexpected data types")
    df = df[~bad_type_mask]

    # --- Check 3: values outside a plausible range ---
    lat_mask = (df["latitude"] < MIN_LATITUDE) | (df["latitude"] > MAX_LATITUDE)
    if lat_mask.any():
        logger.warning(f"Flagging {lat_mask.sum()} rows with out-of-range latitude")
    df = df[~lat_mask]

    lon_mask = (df["longitude"] < MIN_LONGITUDE) | (df["longitude"] > MAX_LONGITUDE)
    if lon_mask.any():
        logger.warning(f"Flagging {lon_mask.sum()} rows with out-of-range longitude")
    df = df[~lon_mask]

    year_mask = (df["year"] < MIN_YEAR) | (df["year"] > MAX_YEAR)
    if year_mask.any():
        logger.warning(f"Flagging {year_mask.sum()} rows with implausible year")
    df = df[~year_mask]

    # alert_score can be missing for some event types - only check range where present
    score_present = df["alert_score"].notna()
    score_mask = score_present & ((df["alert_score"] < MIN_ALERT_SCORE) | (df["alert_score"] > MAX_ALERT_SCORE))
    if score_mask.any():
        logger.warning(f"Flagging {score_mask.sum()} rows with out-of-range alert_score")
    df = df[~score_mask]

    # --- Check 4: alert_level must be one of the expected categories ---
    valid_levels = {"Orange", "Red"}
    level_mask = ~df["alert_level"].isin(valid_levels)
    if level_mask.any():
        logger.warning(f"Flagging {level_mask.sum()} rows with unexpected alert_level value: {df.loc[level_mask, 'alert_level'].unique()}")
    df = df[~level_mask]

    dropped = original_count - len(df)
    logger.info(f"Validation complete: {dropped} rows dropped, {len(df)} rows passed")

    return df.reset_index(drop=True)