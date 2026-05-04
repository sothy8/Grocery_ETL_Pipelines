#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$(pwd)"

python -m src.ingest.source_api &
SOURCE_API_PID=$!
trap 'kill $SOURCE_API_PID 2>/dev/null || true' EXIT

python -m src.ingest.kafka_producer
export SPARK_HOME="${SPARK_HOME:-/Users/vandethsothy/Apache-Spark/spark-3.5.8-bin-hadoop3}"
"$SPARK_HOME/bin/spark-submit" src/etl/batch_to_bronze.py
"$SPARK_HOME/bin/spark-submit" src/etl/silver_gold.py
python -m src.training.train_model
uvicorn src.app.main:app --reload
