# Project Overview

## Goal
Build an end-to-end grocery sales analytics platform from a CSV source using real-time APIs, Kafka, PySpark, warehouse layers, machine learning, and a dashboard.

## Business Questions
- Which item types generate the most sales?
- Which outlet types perform best?
- How do outlet attributes affect sales?
- Can we predict total sales from item and outlet attributes?

## Data Source
The provided source file acts as the initial raw dataset. The project wraps it in a source API so it can behave like a real-time upstream system.

## Pipeline Stages

### 1. Source Layer
- `src/ingest/source_api.py`
- Exposes `/sales` and `/sales/{item_identifier}`

### 2. Streaming Layer
- `src/ingest/kafka_producer.py`
- Publishes source rows to Kafka
- `src/etl/stream_to_bronze.py`
- Consumes Kafka messages into Bronze

### 3. Batch Layer
- `src/etl/batch_to_bronze.py`
- Loads the CSV directly into Bronze for reproducible backfills

### 4. Bronze Layer
- Raw data plus ingestion timestamp
- Stored as Parquet

### 5. Silver Layer
- Standardized column names
- Normalized fat content labels
- Type casting
- Missing weight imputation

### 6. Gold Layer
- Star schema
- Fact table for sales
- Item, outlet, and date dimensions

### 7. Training
- `src/training/train_model.py`
- RandomForestRegressor baseline
- Metrics saved to JSON
- Model saved with Joblib

### 8. Serving and Visualization
- `src/app/main.py`: prediction API
- `src/dashboard/app.py`: Streamlit dashboard

## Recommended Run Order
1. Start Docker services
2. Start the source API
3. Push data into Kafka
4. Run Bronze ingestion
5. Build Silver and Gold layers
6. Load Gold into Postgres
7. Train the model
8. Start the serving API
9. Launch the dashboard

## Main Outputs
- Bronze Parquet files
- Silver Parquet files
- Gold warehouse Parquet files
- PostgreSQL star schema tables
- Trained model artifact
- Dashboard for sales analytics
