import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from transform import clean_data


def make_feature(event_id=1, episode_id=1, event_type="FL", alert_level="Orange",
                  alert_score=2, country="Kenya", from_date="2020-05-01T00:00:00",
                  to_date="2020-05-10T00:00:00", lon=39.0, lat=-3.0):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "eventid": event_id, "episodeid": episode_id, "eventtype": event_type,
            "eventname": f"Test event {event_id}", "alertlevel": alert_level,
            "alertscore": alert_score, "country": country,
            "fromdate": from_date, "todate": to_date,
            "severitydata": {"severity": 10.0, "severityunit": "km2"},
            "population": {"value": 1000},
        },
    }


def make_raw(features):
    return {"type": "FeatureCollection", "features": features}


def test_drops_row_with_missing_event_id():
    f1 = make_feature(event_id=1)
    f2 = make_feature(event_id=2)
    f1["properties"]["eventid"] = None
    df = clean_data(make_raw([f1, f2]))
    assert len(df) == 1
    assert df.iloc[0]["event_id"] == 2


def test_keeps_only_latest_episode_per_event():
    f1 = make_feature(event_id=100, episode_id=1)
    f2 = make_feature(event_id=100, episode_id=2)
    f3 = make_feature(event_id=100, episode_id=3)
    df = clean_data(make_raw([f1, f2, f3]))
    assert len(df) == 1
    assert df.iloc[0]["episode_id"] == 3


def test_alert_level_is_capitalized_consistently():
    f1 = make_feature(event_id=1, alert_level="ORANGE")
    df = clean_data(make_raw([f1]))
    assert df.iloc[0]["alert_level"] == "Orange"


def test_year_extracted_from_from_date():
    f1 = make_feature(event_id=1, from_date="2018-07-15T00:00:00")
    df = clean_data(make_raw([f1]))
    assert df.iloc[0]["year"] == 2018


def test_empty_payload_returns_empty_dataframe():
    df = clean_data(make_raw([]))
    assert df.empty