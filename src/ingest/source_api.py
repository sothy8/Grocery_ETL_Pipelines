from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query

from src.config import RAW_DATA_PATH

app = FastAPI(title="Grocery Sales Source API", version="1.0.0")

def load_data(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/sales")
def list_sales(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)) -> dict[str, object]:
    frame = load_data()
    rows = frame.iloc[offset : offset + limit].fillna("").to_dict(orient="records")
    return {"count": len(rows), "data": rows}

@app.get("/sales/{item_identifier}")
def get_item(item_identifier: str) -> dict[str, object]:
    frame = load_data()
    matches = frame[frame["Item Identifier"].astype(str) == item_identifier].fillna("")
    return {"count": len(matches), "data": matches.to_dict(orient="records")}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
