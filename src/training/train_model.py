from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.config import FEATURE_COLUMNS, MODELS_PATH, SILVER_PATH, TARGET_COLUMN


def main() -> None:
    frame = pd.read_parquet(SILVER_PATH)
    data = frame[FEATURE_COLUMNS + [TARGET_COLUMN]].dropna(subset=[TARGET_COLUMN])

    X = data[FEATURE_COLUMNS]
    y = data[TARGET_COLUMN]

    categorical_features = [
        "item_fat_content",
        "item_type",
        "outlet_location_type",
        "outlet_size",
        "outlet_type",
    ]
    numeric_features = ["outlet_establishment_year", "item_visibility", "item_weight"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("numeric", "passthrough", numeric_features),
        ]
    )

    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    pipeline.fit(X_train, y_train)

    predictions = pipeline.predict(X_test)
    metrics = {
        "mae": mean_absolute_error(y_test, predictions),
        "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "r2": r2_score(y_test, predictions),
    }

    MODELS_PATH.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODELS_PATH / "grocery_sales_model.joblib")
    (MODELS_PATH / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
