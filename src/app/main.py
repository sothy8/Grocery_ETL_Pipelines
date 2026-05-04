from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add project root to path for imports to work when running uvicorn
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import FEATURE_COLUMNS, MODELS_PATH, SILVER_PATH

app = FastAPI(title="Grocery Sales Prediction API", version="1.0.0")
MODEL_PATH = MODELS_PATH / "grocery_sales_model.joblib"


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
    require_artifact(SILVER_PATH, "Silver layer")
    frame = pd.read_parquet(SILVER_PATH)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
