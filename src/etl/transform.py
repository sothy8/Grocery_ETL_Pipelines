from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, concat_ws, lit, lower, regexp_replace, sha2, trim, when
from pyspark.sql.types import DoubleType


def clean_frame(frame: DataFrame) -> DataFrame:
    cleaned = frame
    for source_name, target_name in {
        "Item Fat Content": "item_fat_content",
        "Item Identifier": "item_identifier",
        "Item Type": "item_type",
        "Outlet Establishment Year": "outlet_establishment_year",
        "Outlet Identifier": "outlet_identifier",
        "Outlet Location Type": "outlet_location_type",
        "Outlet Size": "outlet_size",
        "Outlet Type": "outlet_type",
        "Item Visibility": "item_visibility",
        "Item Weight": "item_weight",
        "Total Sales": "total_sales",
        "Rating": "rating",
    }.items():
        cleaned = cleaned.withColumnRenamed(source_name, target_name)

    cleaned = cleaned.select(
        [
            trim(col(c)).alias(c)
            if c in {
                "item_fat_content",
                "item_identifier",
                "item_type",
                "outlet_identifier",
                "outlet_location_type",
                "outlet_size",
                "outlet_type",
            }
            else col(c)
            for c in cleaned.columns
        ]
    )

    cleaned = cleaned.withColumn("item_fat_content", lower(col("item_fat_content")))
    cleaned = cleaned.withColumn(
        "item_fat_content",
        when(col("item_fat_content").isin("lf", "low fat"), lit("Low Fat"))
        .when(col("item_fat_content").isin("regular", "reg"), lit("Regular"))
        .otherwise(regexp_replace(col("item_fat_content"), "^\\s+|\\s+$", "")),
    )

    cleaned = cleaned.withColumn("item_visibility", col("item_visibility").cast(DoubleType()))
    cleaned = cleaned.withColumn("item_weight", col("item_weight").cast(DoubleType()))
    cleaned = cleaned.withColumn("total_sales", col("total_sales").cast(DoubleType()))
    cleaned = cleaned.withColumn("rating", col("rating").cast(DoubleType()))
    cleaned = cleaned.withColumn("outlet_establishment_year", col("outlet_establishment_year").cast("int"))
    return cleaned


def add_imputed_weight(frame: DataFrame) -> DataFrame:
    median_weight = frame.approxQuantile("item_weight", [0.5], 0.01)[0]
    return frame.fillna({"item_weight": median_weight})


def build_gold_layers(frame: DataFrame) -> dict[str, DataFrame]:
    silver = frame.withColumn("event_date", col("ingest_ts").cast("date"))

    dim_item = silver.select("item_identifier", "item_type", "item_fat_content").dropDuplicates()
    dim_outlet = silver.select(
        "outlet_identifier",
        "outlet_location_type",
        "outlet_size",
        "outlet_type",
        "outlet_establishment_year",
    ).dropDuplicates()
    dim_date = silver.select("event_date").dropDuplicates()

    dim_item = dim_item.withColumn(
        "item_key",
        sha2(concat_ws("||", col("item_identifier"), col("item_type"), col("item_fat_content")), 256),
    )
    dim_outlet = dim_outlet.withColumn(
        "outlet_key",
        sha2(
            concat_ws(
                "||",
                col("outlet_identifier"),
                col("outlet_location_type"),
                col("outlet_size"),
                col("outlet_type"),
                col("outlet_establishment_year").cast("string"),
            ),
            256,
        ),
    )
    dim_date = dim_date.withColumn("date_key", sha2(concat_ws("||", col("event_date").cast("string")), 256))

    fact_sales = (
        silver.join(dim_item, ["item_identifier", "item_type", "item_fat_content"], "left")
        .join(
            dim_outlet,
            [
                "outlet_identifier",
                "outlet_location_type",
                "outlet_size",
                "outlet_type",
                "outlet_establishment_year",
            ],
            "left",
        )
        .join(dim_date, ["event_date"], "left")
        .select(
            "item_key",
            "outlet_key",
            "date_key",
            "item_visibility",
            "item_weight",
            "total_sales",
            "rating",
            "ingest_ts",
        )
    )

    return {
        "silver": silver,
        "dim_item": dim_item,
        "dim_outlet": dim_outlet,
        "dim_date": dim_date,
        "fact_sales": fact_sales,
    }
