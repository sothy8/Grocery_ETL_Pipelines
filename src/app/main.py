from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import json

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path for imports to work when running uvicorn
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import FEATURE_COLUMNS, MODELS_PATH, SILVER_PATH
from src.training.model_utils import MODEL_PATH

app = FastAPI(title="Grocery Sales Prediction API", version="1.0.0")
METRICS_PATH = MODELS_PATH / "metrics.json"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_artifact(path, label: str) -> None:
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"{label} is not available yet.")


class PredictionRequest(BaseModel):
    item_fat_content: str
    item_type: str
    outlet_location_type: str
    outlet_size: str
    outlet_type: str
    outlet_establishment_year: int
    item_visibility: float
    item_weight: float


_model: Any = None


def get_model():
    global _model
    if _model is None:
        require_artifact(MODEL_PATH, "Model")
        _model = joblib.load(MODEL_PATH)
    return _model


def load_silver_frame() -> pd.DataFrame:
    require_artifact(SILVER_PATH, "Silver layer")
    return pd.read_parquet(SILVER_PATH)


def load_metrics() -> dict[str, float]:
    if not METRICS_PATH.exists():
        return {}
    payload = METRICS_PATH.read_text(encoding="utf-8")
    data = json.loads(payload)
    return {key: float(value) for key, value in data.items()}


def apply_filters(
    frame: pd.DataFrame,
    item_type: list[str],
    outlet_type: list[str],
    outlet_location_type: list[str],
    outlet_size: list[str],
    item_fat_content: list[str],
    sales_min: float | None,
    sales_max: float | None,
) -> pd.DataFrame:
    filtered = frame
    if item_type:
        filtered = filtered[filtered["item_type"].isin(item_type)]
    if outlet_type:
        filtered = filtered[filtered["outlet_type"].isin(outlet_type)]
    if outlet_location_type:
        filtered = filtered[filtered["outlet_location_type"].isin(outlet_location_type)]
    if outlet_size:
        filtered = filtered[filtered["outlet_size"].isin(outlet_size)]
    if item_fat_content:
        filtered = filtered[filtered["item_fat_content"].isin(item_fat_content)]
    if sales_min is not None:
        filtered = filtered[filtered["total_sales"] >= sales_min]
    if sales_max is not None:
        filtered = filtered[filtered["total_sales"] <= sales_max]
    return filtered


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Grocery Sales Prediction API",
        "docs": "http://127.0.0.1:8000/docs",
        "health": "http://127.0.0.1:8000/health",
        "summary": "http://127.0.0.1:8000/summary",
        "sample_payload": "http://127.0.0.1:8000/sample-payload",
        "predict": "POST http://127.0.0.1:8000/predict",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/summary")
def summary() -> dict[str, object]:
    frame = load_silver_frame()
    return {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "total_sales_mean": float(frame["total_sales"].mean()),
        "total_sales_sum": float(frame["total_sales"].sum()),
    }


@app.get("/sample-payload")
def sample_payload() -> dict[str, object]:
    return {
        "item_fat_content": "Low Fat",
        "item_type": "Fruits and Vegetables",
        "outlet_location_type": "Tier 1",
        "outlet_size": "Medium",
        "outlet_type": "Supermarket Type1",
        "outlet_establishment_year": 2012,
        "item_visibility": 0.1,
        "item_weight": 15.1,
    }


@app.post("/predict")
def predict(payload: PredictionRequest) -> dict[str, float]:
    model = get_model()
    row = pd.DataFrame([payload.model_dump()])[FEATURE_COLUMNS]
    prediction = float(model.predict(row)[0])
    return {"predicted_total_sales": prediction}


@app.get("/dashboard-data")
def dashboard_data(
    item_type: list[str] = Query(default=[]),
    outlet_type: list[str] = Query(default=[]),
    outlet_location_type: list[str] = Query(default=[]),
    outlet_size: list[str] = Query(default=[]),
    item_fat_content: list[str] = Query(default=[]),
    sales_min: float | None = None,
    sales_max: float | None = None,
    limit: int = 50,
) -> dict[str, object]:
    frame = load_silver_frame()
    metrics = load_metrics()

    filtered = apply_filters(
        frame,
        item_type,
        outlet_type,
        outlet_location_type,
        outlet_size,
        item_fat_content,
        sales_min,
        sales_max,
    )

    item_sales = (
        filtered.groupby("item_type", as_index=False)
        .agg(total_sales=("total_sales", "sum"), avg_sales=("total_sales", "mean"), count=("total_sales", "count"))
        .sort_values("total_sales", ascending=False)
    )
    outlet_sales = (
        filtered.groupby("outlet_type", as_index=False)
        .agg(total_sales=("total_sales", "sum"), count=("total_sales", "count"))
        .sort_values("total_sales", ascending=False)
    )
    location_sales = (
        filtered.groupby("outlet_location_type", as_index=False)
        .agg(total_sales=("total_sales", "sum"), count=("total_sales", "count"))
        .sort_values("total_sales", ascending=False)
    )
    size_sales = (
        filtered.groupby("outlet_size", as_index=False)
        .agg(total_sales=("total_sales", "sum"), count=("total_sales", "count"))
        .sort_values("total_sales", ascending=False)
    )
    fat_sales = (
        filtered.groupby("item_fat_content", as_index=False)
        .agg(total_sales=("total_sales", "sum"), avg_sales=("total_sales", "mean"), count=("total_sales", "count"))
        .sort_values("total_sales", ascending=False)
    )
    year_sales = (
        filtered.groupby("outlet_establishment_year", as_index=False)
        .agg(total_sales=("total_sales", "sum"), count=("total_sales", "count"))
        .sort_values("outlet_establishment_year")
    )

    sales_bins = pd.cut(filtered["total_sales"], bins=20)
    sales_distribution = sales_bins.value_counts().sort_index().reset_index()
    if not sales_distribution.empty:
        sales_distribution.columns = ["bin", "count"]
    if not sales_distribution.empty:
        sales_distribution["bin_start"] = sales_distribution["bin"].apply(lambda interval: float(interval.left))
        sales_distribution["bin_end"] = sales_distribution["bin"].apply(lambda interval: float(interval.right))

    top_products = (
        filtered.groupby(["item_identifier", "item_type"], as_index=False)
        .agg(total_sales=("total_sales", "sum"), avg_rating=("rating", "mean"))
        .sort_values("total_sales", ascending=False)
        .head(10)
    )

    sample_rows = filtered.head(max(min(limit, 100), 1))

    predictions_payload: dict[str, object] = {"rows": [], "avg_predicted_total_sales": 0.0, "sum_predicted_total_sales": 0.0}
    if not filtered.empty:
        prediction_frame = filtered.copy()
        if "predicted_total_sales" not in prediction_frame.columns and MODEL_PATH.exists():
            model = get_model()
            prediction_values = model.predict(prediction_frame[FEATURE_COLUMNS])
            prediction_frame = prediction_frame.assign(predicted_total_sales=prediction_values)

        if "predicted_total_sales" in prediction_frame.columns:
            prediction_sample = prediction_frame.head(max(min(limit, 100), 1))
            predictions_payload = {
                "rows": prediction_sample.to_dict(orient="records"),
                "avg_predicted_total_sales": float(prediction_frame["predicted_total_sales"].mean()),
                "sum_predicted_total_sales": float(prediction_frame["predicted_total_sales"].sum()),
            }

    response = {
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "total_records": int(len(filtered)),
            "avg_sales": float(filtered["total_sales"].mean()) if not filtered.empty else 0.0,
            "total_sales": float(filtered["total_sales"].sum()) if not filtered.empty else 0.0,
            "avg_rating": float(filtered["rating"].mean()) if not filtered.empty else 0.0,
            "model_r2": float(metrics.get("r2", 0.0)),
        },
        "filters": {
            "item_type": sorted(frame["item_type"].dropna().unique().tolist()),
            "outlet_type": sorted(frame["outlet_type"].dropna().unique().tolist()),
            "outlet_location_type": sorted(frame["outlet_location_type"].dropna().unique().tolist()),
            "outlet_size": sorted(frame["outlet_size"].dropna().unique().tolist()),
            "item_fat_content": sorted(frame["item_fat_content"].dropna().unique().tolist()),
            "sales_min": float(frame["total_sales"].min()),
            "sales_max": float(frame["total_sales"].max()),
        },
        "charts": {
            "sales_by_item_type": item_sales.round(2).to_dict(orient="records"),
            "sales_by_outlet_type": outlet_sales.round(2).to_dict(orient="records"),
            "sales_by_location_type": location_sales.round(2).to_dict(orient="records"),
            "sales_by_outlet_size": size_sales.round(2).to_dict(orient="records"),
            "sales_by_fat_content": fat_sales.round(2).to_dict(orient="records"),
            "sales_by_year": year_sales.round(2).to_dict(orient="records"),
            "sales_distribution": sales_distribution[["bin_start", "bin_end", "count"]].to_dict(orient="records")
            if not sales_distribution.empty
            else [],
        },
        "tables": {
            "top_products": top_products.round(2).to_dict(orient="records"),
            "sample_rows": sample_rows.assign(
                **{c: sample_rows[c].round(2) for c in sample_rows.select_dtypes(include="number").columns}
            ).to_dict(orient="records"),
        },
        "predictions": predictions_payload,
    }
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
