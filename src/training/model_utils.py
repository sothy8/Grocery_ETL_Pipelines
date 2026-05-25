from __future__ import annotations

from typing import Any

import joblib

from src.config import MODELS_PATH

MODEL_PATH = MODELS_PATH / "grocery_sales_model.joblib"

_model: Any = None


def get_model() -> Any | None:
    """Lazily load and cache the trained model. Returns None if not yet trained."""
    global _model
    if _model is None and MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
    return _model


def reset_model_cache() -> None:
    """Force the next get_model() call to reload from disk (useful after retraining)."""
    global _model
    _model = None
