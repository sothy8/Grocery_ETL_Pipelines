from __future__ import annotations

from pyspark.sql import SparkSession

from src.etl.extract import extract_batch_csv
from src.etl.load import load_bronze_batch


def main() -> None:
    spark = (
        SparkSession.builder.appName("grocery-batch-to-bronze")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    bronze = extract_batch_csv(spark)
    load_bronze_batch(bronze)
    spark.stop()


if __name__ == "__main__":
    main()
