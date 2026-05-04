from __future__ import annotations

from pyspark.sql import SparkSession

from src.config import BRONZE_PATH
from src.etl.load import load_gold, load_silver
from src.etl.transform import add_imputed_weight, build_gold_layers, clean_frame


def main() -> None:
    spark = (
        SparkSession.builder.appName("grocery-silver-gold")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    bronze = spark.read.parquet(str(BRONZE_PATH))
    cleaned = add_imputed_weight(clean_frame(bronze))

    load_silver(cleaned)

    gold = build_gold_layers(cleaned)
    load_gold(gold)

    spark.stop()


if __name__ == "__main__":
    main()
