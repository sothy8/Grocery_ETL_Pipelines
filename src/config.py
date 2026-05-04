from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = BASE_DIR / "grocerySale.csv"
BRONZE_PATH = DATA_DIR / "bronze"
SILVER_PATH = DATA_DIR / "silver"
GOLD_PATH = DATA_DIR / "gold"
MODELS_PATH = BASE_DIR / "models"
CHECKPOINT_PATH = BASE_DIR / "checkpoints"

KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "grocery-sales")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SOURCE_API_URL = os.getenv("SOURCE_API_URL", "http://localhost:8001")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "grocery_warehouse")
POSTGRES_USER = os.getenv("POSTGRES_USER", "grocery")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "grocery")
POSTGRES_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

FEATURE_COLUMNS = [
    "item_fat_content",
    "item_type",
    "outlet_location_type",
    "outlet_size",
    "outlet_type",
    "outlet_establishment_year",
    "item_visibility",
    "item_weight",
]
TARGET_COLUMN = "total_sales"
