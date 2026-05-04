from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from src.config import BASE_DIR, GOLD_PATH, POSTGRES_URL


def load_table(engine, table_name: str, path: Path) -> None:
    frame = pd.read_parquet(path)
    frame.to_sql(table_name, engine, schema="grocery", if_exists="append", index=False)


def initialize_schema(engine) -> None:
    ddl_path = BASE_DIR / "src" / "warehouse" / "star_schema.sql"
    ddl = ddl_path.read_text(encoding="utf-8")
    with engine.begin() as connection:
        for statement in [part.strip() for part in ddl.split(";") if part.strip()]:
            connection.exec_driver_sql(statement)
        connection.exec_driver_sql("TRUNCATE TABLE grocery.fact_sales, grocery.dim_item, grocery.dim_outlet, grocery.dim_date RESTART IDENTITY CASCADE")


def main() -> None:
    engine = create_engine(POSTGRES_URL)
    initialize_schema(engine)
    load_table(engine, "dim_item", GOLD_PATH / "dim_item")
    load_table(engine, "dim_outlet", GOLD_PATH / "dim_outlet")
    load_table(engine, "dim_date", GOLD_PATH / "dim_date")
    load_table(engine, "fact_sales", GOLD_PATH / "fact_sales")


if __name__ == "__main__":
    main()
