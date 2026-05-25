from __future__ import annotations

from pyspark.sql import SparkSession
from src.etl.extract import extract_stream_kafka
from src.etl.load import load_bronze_stream


def main() -> None:
    spark = (
        SparkSession.builder.appName("grocery-stream-to-bronze")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )

    parsed = extract_stream_kafka(spark)
    query = load_bronze_stream(parsed)

    query.awaitTermination()


if __name__ == "__main__":
    main()
