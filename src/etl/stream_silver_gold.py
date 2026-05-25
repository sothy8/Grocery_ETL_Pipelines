from __future__ import annotations

from pathlib import Path

import pandas as pd
from pyspark.sql import SparkSession

from src.config import BRONZE_PATH, FEATURE_COLUMNS, MODELS_PATH, SILVER_PATH
from src.etl.load import load_gold
from src.etl.transform import add_imputed_weight, build_gold_layers, clean_frame
from src.training.model_utils import get_model


def append_batch_to_silver(batch_pdf: pd.DataFrame) -> pd.DataFrame:
    silver_path = Path(SILVER_PATH)
    if silver_path.exists():
        existing = pd.read_parquet(silver_path)
        return pd.concat([existing, batch_pdf], ignore_index=True)
    return batch_pdf


def process_batch(batch_df, _batch_id: int) -> None:
    if batch_df.rdd.isEmpty():
        return

    cleaned = add_imputed_weight(clean_frame(batch_df))
    batch_pdf = cleaned.toPandas()

    model = get_model()
    if model is not None and not batch_pdf.empty:
        batch_pdf["predicted_total_sales"] = model.predict(batch_pdf[FEATURE_COLUMNS])

    combined_pdf = append_batch_to_silver(batch_pdf)
    combined_spark = batch_df.sparkSession.createDataFrame(combined_pdf)

    combined_spark.write.mode("overwrite").parquet(str(SILVER_PATH))
    load_gold(build_gold_layers(combined_spark))


def main() -> None:
    spark = (
        SparkSession.builder.appName("grocery-stream-silver-gold")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    bronze_schema = spark.read.parquet(str(BRONZE_PATH)).schema

    stream = spark.readStream.schema(bronze_schema).parquet(str(BRONZE_PATH))
    query = stream.writeStream.foreachBatch(process_batch).option(
        "checkpointLocation", str(Path("checkpoints") / "silver_gold_stream")
    ).start()

    query.awaitTermination()


if __name__ == "__main__":
    main()