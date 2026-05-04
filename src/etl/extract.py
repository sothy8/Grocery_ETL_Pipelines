from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, from_json
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

from src.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, RAW_DATA_PATH

SOURCE_SCHEMA = StructType(
    [
        StructField("Item Fat Content", StringType()),
        StructField("Item Identifier", StringType()),
        StructField("Item Type", StringType()),
        StructField("Outlet Establishment Year", IntegerType()),
        StructField("Outlet Identifier", StringType()),
        StructField("Outlet Location Type", StringType()),
        StructField("Outlet Size", StringType()),
        StructField("Outlet Type", StringType()),
        StructField("Item Visibility", DoubleType()),
        StructField("Item Weight", DoubleType()),
        StructField("Total Sales", DoubleType()),
        StructField("Rating", DoubleType()),
    ]
)


def extract_batch_csv(spark: SparkSession) -> DataFrame:
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(str(RAW_DATA_PATH))
        .withColumn("ingest_ts", current_timestamp())
    )


def extract_stream_kafka(spark: SparkSession):
    stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", KAFKA_TOPIC)
        .option("startingOffsets", "latest")
        .load()
    )

    return (
        stream.select(from_json(stream.value.cast("string"), SOURCE_SCHEMA).alias("data"))
        .select("data.*")
        .withColumn("ingest_ts", current_timestamp())
    )
