import logging

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from db import get_connection
from train_models import build_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("export_predictions")


def main():
    with get_connection() as conn:
        df = pd.read_sql("SELECT * FROM clean_gdacs", conn)
    logger.info(f"Loaded {len(df)} rows")

    X, y = build_features(df)

    # Same split settings as train_models.py, so this matches the test set the model was actually evaluated on
    X_train, X_test, y_train, y_test, df_train, df_test = train_test_split(
        X, y, df, test_size=0.2, random_state=42, stratify=y
    )

    rf = joblib.load("models/random_forest.pkl")
    predictions = rf.predict(X_test)

    result = df_test[["event_id", "event_type", "country", "year", "alert_level"]].copy()
    result["predicted_alert_level"] = ["Red" if p == 1 else "Orange" for p in predictions]
    result["correct_prediction"] = result["alert_level"] == result["predicted_alert_level"]

    result.to_csv("data/ml_predictions.csv", index=False)
    logger.info(f"Saved {len(result)} predictions to data/ml_predictions.csv")
    logger.info(f"Accuracy check: {result['correct_prediction'].mean():.3f}")


if __name__ == "__main__":
    main()