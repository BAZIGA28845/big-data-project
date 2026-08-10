import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from validate import validate_data


def make_row(**overrides):
    row = {
        "event_id": 1, "event_type": "FL", "alert_level": "Orange",
        "alert_score": 2, "year": 2020, "latitude": -3.0, "longitude": 39.0,
    }
    row.update(overrides)
    return row


def test_normal_row_passes_unchanged():
    df = pd.DataFrame([make_row()])
    result = validate_data(df)
    assert len(result) == 1


def test_row_with_missing_value_is_dropped():
    df = pd.DataFrame([make_row(event_id=None), make_row(event_id=2)])
    result = validate_data(df)
    assert len(result) == 1
    assert result.iloc[0]["event_id"] == 2


def test_out_of_range_latitude_is_dropped():
    df = pd.DataFrame([make_row(latitude=200.0), make_row(event_id=2)])
    result = validate_data(df)
    assert len(result) == 1
    assert result.iloc[0]["event_id"] == 2


def test_unexpected_alert_level_is_dropped():
    df = pd.DataFrame([make_row(alert_level="Purple"), make_row(event_id=2)])
    result = validate_data(df)
    assert len(result) == 1
    assert result.iloc[0]["event_id"] == 2


def test_empty_dataframe_returns_empty():
    df = pd.DataFrame(columns=["event_id", "event_type", "alert_level", "alert_score", "year", "latitude", "longitude"])
    result = validate_data(df)
    assert result.empty