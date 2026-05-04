from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql.streaming import StreamingQuery

from src.config import BRONZE_PATH, CHECKPOINT_PATH, GOLD_PATH, SILVER_PATH


def load_bronze_batch(frame: DataFrame) -> None:
    frame.write.mode("overwrite").parquet(str(BRONZE_PATH))


def load_bronze_stream(frame: DataFrame) -> StreamingQuery:
    return (
        frame.writeStream.format("parquet")
        .option("path", str(BRONZE_PATH))
        .option("checkpointLocation", str(CHECKPOINT_PATH / "bronze_stream"))
        .outputMode("append")
        .start()
    )


def load_silver(frame: DataFrame) -> None:
    frame.write.mode("overwrite").parquet(str(SILVER_PATH))


def load_gold(gold_layers: dict[str, DataFrame]) -> None:
    for name, frame in gold_layers.items():
        frame.write.mode("overwrite").parquet(str(GOLD_PATH / name))
