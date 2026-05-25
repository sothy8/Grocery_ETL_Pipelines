# Grocery Sales ETL Pipeline

An end-to-end data engineering project that ingests grocery sales data through both batch and real-time streaming pipelines, applies ETL transformations with Apache Spark, trains a sales prediction model, and serves results through a FastAPI backend and Next.js dashboard.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Technology Stack](#technology-stack)
4. [Dataset](#dataset)
5. [Quick Start](#quick-start)
6. [Running the Pipeline](#running-the-pipeline)
7. [API Reference](#api-reference)
8. [Database Schema](#database-schema)
9. [ML Model](#ml-model)
10. [Configuration](#configuration)
11. [Troubleshooting](#troubleshooting)

---

## Architecture

The system follows a medallion architecture (Bronze → Silver → Gold) with two pipeline modes: batch and real-time streaming.

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCE                            │
│                    grocerySale.csv                          │
│                   (8,524 records)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   ┌─────────────┐         ┌─────────────────┐
   │ Source API  │         │  Kafka Producer  │
   │  port 8001  │────────▶│  grocery-sales   │
   └─────────────┘         └────────┬─────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │         SPARK ETL              │
                    │                               │
                    │  Kafka ──▶ Bronze (Parquet)   │  stream_to_bronze.py
                    │  Bronze ──▶ Silver (cleaned)  │  stream_silver_gold.py
                    │  Silver ──▶ Gold (star schema)│
                    └───────────────┬───────────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               ▼                    ▼                     ▼
         ┌──────────┐        ┌────────────┐       ┌────────────┐
         │  Bronze  │        │   Silver   │       │    Gold    │
         │ (raw)    │        │ (cleaned + │       │ (star      │
         │ Parquet  │        │  imputed)  │       │  schema)   │
         └──────────┘        └─────┬──────┘       └─────┬──────┘
                                   │                     │
                    ┌──────────────┘                     │
                    ▼                                     ▼
             ┌────────────┐                      ┌────────────────┐
             │ ML Training│                      │   PostgreSQL   │
             │ RandomForest│                     │  Data Warehouse│
             │ R² = 0.581 │                      │  (star schema) │
             └─────┬──────┘                      └────────────────┘
                   │
                   ▼
         ┌──────────────────┐         ┌──────────────────┐
         │  FastAPI Backend │         │  Next.js Frontend│
         │    port 8000     │◀────────│    port 3000     │
         │  /predict        │         │  Dashboard UI    │
         │  /dashboard-data │         │                  │
         └──────────────────┘         └──────────────────┘
```

### Pipeline Modes

**Batch mode** (default): Reads the full CSV once, processes it through all ETL stages, trains the model, and loads the warehouse. Runs to completion.

**Realtime mode** (`--realtime`): Runs continuously. The Kafka producer polls the source API in a loop, `stream_to_bronze` consumes from Kafka into bronze parquet, and `stream_silver_gold` watches the bronze directory and processes new batches into silver/gold with ML scoring.

---

## Technology Stack

| Category | Technology | Version |
|---|---|---|
| Data processing | Apache Spark (PySpark) | 3.5.8 |
| Message queue | Apache Kafka | 7.6.1 (Confluent) |
| Database | PostgreSQL | 16 |
| Python | CPython | 3.12 |
| Storage format | Apache Parquet (Snappy) | — |
| ML framework | scikit-learn | latest |
| Web API | FastAPI + Uvicorn | latest |
| Frontend | Next.js | 16.2.6 |
| Infrastructure | Docker Compose | — |
| Model serialization | joblib | latest |
| DB abstraction | SQLAlchemy + psycopg2 | latest |

---

## Dataset

**Source**: `grocerySale.csv` — 8,524 grocery sales transactions across 12 columns.

### Schema

| Column | Type | Notes |
|---|---|---|
| Item Identifier | string | Product ID |
| Item Fat Content | string | "Low Fat", "Regular" (+ variants) |
| Item Type | string | 16 product categories |
| Item Visibility | float | Shelf visibility [0, 1] |
| Item Weight | float | Weight in kg — 1,463 nulls (17%) |
| Outlet Identifier | string | Store ID |
| Outlet Establishment Year | int | Year store opened |
| Outlet Location Type | string | Tier 1 / 2 / 3 |
| Outlet Size | string | Small / Medium / High |
| Outlet Type | string | Supermarket Type1/2/3, Grocery Store |
| Total Sales | float | Revenue — prediction target |
| Rating | float | Customer rating |

### Data Quality Handling

| Issue | Fix |
|---|---|
| 1,463 missing `Item Weight` values | Median imputation in silver transform |
| Inconsistent fat content labels (`lf`, `low fat`, `LF`) | Standardized to `Low Fat` / `Regular` |
| Mixed-case and padded strings | Trimmed and lowercased in transform |
| No timestamp on source data | `ingest_ts` added at extraction time |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Apache Spark 3.5.8 installed locally
- Node.js 18+ (for the frontend)

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
cd frontend
npm install
cd ..
```

### 2. Start infrastructure

```bash
docker compose up -d
docker compose ps   # all three services should show "Up"
```

This starts:
- Kafka broker on `localhost:9092`
- Zookeeper on `localhost:2181`
- PostgreSQL on `localhost:5432`

### 3. Run the pipeline

See [Running the Pipeline](#running-the-pipeline) below.

---

## Running the Pipeline

Everything is orchestrated through `main.py`. Set your Spark home if it differs from the default:

```bash
source .venv/bin/activate
```

### Batch mode

Runs the full pipeline once: ingest → ETL → train → load warehouse → start servers.

```bash
python3 main.py
```

Steps executed in order:
1. Starts source API (port 8001)
2. Waits for Kafka
3. Starts FastAPI backend + Next.js frontend
4. Runs `kafka_producer` — publishes all 8,524 rows to Kafka
5. Runs `batch_to_bronze.py` — CSV → bronze parquet
6. Runs `silver_gold.py` — bronze → silver → gold star schema
7. Runs `train_model.py` — trains RandomForest, saves model + metrics
8. Runs `load_gold_to_postgres.py` — loads gold into PostgreSQL

### Realtime streaming mode

Runs continuously with Spark Structured Streaming.

```bash
python3 main.py --realtime
```

Steps:
1. Starts source API (port 8001)
2. Waits for Kafka
3. Starts FastAPI backend + Next.js frontend
4. Starts Kafka producer in continuous mode (polls source API every 5s)
5. Starts `stream_to_bronze.py` — Kafka → bronze (micro-batch, ~200ms trigger)
6. Waits 30 seconds for bronze to initialize
7. Starts `stream_silver_gold.py` — bronze → silver → gold + ML scoring

Press `Ctrl+C` to stop all processes cleanly.

### Servers only

If the pipeline has already run and you just want the API and frontend:

```bash
python3 main.py --servers-only
```

### CLI options

| Flag | Default | Description |
|---|---|---|
| `--realtime` | off | Enable streaming mode |
| `--servers-only` | off | Skip pipeline, start servers only |
| `--no-servers` | off | Run pipeline without starting servers |
| `--spark-home` | `/Users/vandethsothy/Apache-Spark/spark-3.5.8-bin-hadoop3` | Path to Spark installation |
| `--venv` | `.venv` | Path to virtual environment |
| `--backend-host` | `127.0.0.1` | FastAPI bind host |
| `--backend-port` | `8000` | FastAPI bind port |
| `--no-reload` | off | Disable uvicorn auto-reload |
| `--skip-source-api` | off | Skip starting the source API |

### Stopping and restarting

If you Ctrl+C and need to restart, clear stale ports first:

```bash
lsof -ti :8001 | xargs kill -9 2>/dev/null
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :3000 | xargs kill -9 2>/dev/null
```

To restart streaming from scratch (clears Spark checkpoint state):

```bash
rm -rf checkpoints/
```

---

## API Reference

### Source API — port 8001

Serves the raw CSV over HTTP for the Kafka producer to consume.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/sales?limit=100&offset=0` | Paginated sales records |
| `GET` | `/sales/{item_identifier}` | Records for a specific item |

### Backend API — port 8000

Prediction and dashboard data API consumed by the Next.js frontend.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/summary` | Row count, column list, avg/total sales |
| `GET` | `/sample-payload` | Example prediction request body |
| `POST` | `/predict` | Predict total sales for one record |
| `GET` | `/dashboard-data` | Aggregated charts + filter options |
| `GET` | `/docs` | Swagger UI |

#### POST /predict

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "item_fat_content": "Low Fat",
    "item_type": "Fruits and Vegetables",
    "outlet_location_type": "Tier 1",
    "outlet_size": "Medium",
    "outlet_type": "Supermarket Type1",
    "outlet_establishment_year": 2012,
    "item_visibility": 0.1,
    "item_weight": 15.1
  }'
```

```json
{"predicted_total_sales": 125.23}
```

Returns `503` if the model or silver layer is not yet available.

#### GET /dashboard-data

Accepts query parameters for filtering:

| Param | Type | Example |
|---|---|---|
| `item_type` | list[str] | `?item_type=Dairy&item_type=Snacks` |
| `outlet_type` | list[str] | `?outlet_type=Supermarket+Type1` |
| `outlet_location_type` | list[str] | `?outlet_location_type=Tier+1` |
| `outlet_size` | list[str] | `?outlet_size=Medium` |
| `item_fat_content` | list[str] | `?item_fat_content=Low+Fat` |
| `sales_min` | float | `?sales_min=50.0` |
| `sales_max` | float | `?sales_max=300.0` |
| `limit` | int | `?limit=100` (default 50, max 100) |

Returns metrics, filter options, chart aggregations, top products, sample rows, and ML predictions.

---

## Database Schema

PostgreSQL connection: `postgresql://grocery:grocery@localhost:5432/grocery_warehouse`

All tables live in the `grocery` schema.

### fact_sales

| Column | Type | Description |
|---|---|---|
| item_key | VARCHAR | FK → dim_item |
| outlet_key | VARCHAR | FK → dim_outlet |
| date_key | VARCHAR | FK → dim_date |
| item_visibility | DOUBLE | Shelf visibility |
| item_weight | DOUBLE | Weight in kg |
| total_sales | DOUBLE | Revenue |
| rating | DOUBLE | Customer rating |
| ingest_ts | TIMESTAMP | Ingestion timestamp |

### dim_item

| Column | Type |
|---|---|
| item_key | VARCHAR (PK) |
| item_identifier | VARCHAR |
| item_type | VARCHAR |
| item_fat_content | VARCHAR |

### dim_outlet

| Column | Type |
|---|---|
| outlet_key | VARCHAR (PK) |
| outlet_identifier | VARCHAR |
| outlet_type | VARCHAR |
| outlet_location_type | VARCHAR |
| outlet_size | VARCHAR |
| outlet_establishment_year | INTEGER |

### dim_date

| Column | Type |
|---|---|
| date_key | VARCHAR (PK) |
| event_date | DATE |

Surrogate keys are SHA-256 hashes of the natural key columns, generated in `src/etl/transform.py`.

---

## ML Model

**Algorithm**: RandomForestRegressor (200 trees, `n_jobs=-1`)

**Training data**: Silver layer (cleaned, imputed)

**Features**:

| Feature | Type |
|---|---|
| item_fat_content | categorical (OHE) |
| item_type | categorical (OHE) |
| outlet_location_type | categorical (OHE) |
| outlet_size | categorical (OHE) |
| outlet_type | categorical (OHE) |
| outlet_establishment_year | numeric (passthrough) |
| item_visibility | numeric (passthrough) |
| item_weight | numeric (passthrough) |

**Target**: `total_sales`

**Split**: 80% train / 20% test

**Performance**:

| Metric | Value |
|---|---|
| R² | 0.581 |
| RMSE | $40.72 |
| MAE | $28.24 |

The trained pipeline is saved to `models/grocery_sales_model.joblib` and metrics to `models/metrics.json`.

The model loader is shared across the backend API and the streaming scorer via `src/training/model_utils.py`:

```python
from src.training.model_utils import get_model

model = get_model()   # lazy-loads on first call, cached in memory
```

---

## Configuration

All configuration lives in `src/config.py`. Settings can be overridden with environment variables.

| Variable | Default | Description |
|---|---|---|
| `KAFKA_TOPIC` | `grocery-sales` | Kafka topic name |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `SOURCE_API_URL` | `http://localhost:8001` | Source API base URL |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `grocery_warehouse` | Database name |
| `POSTGRES_USER` | `grocery` | Database user |
| `POSTGRES_PASSWORD` | `grocery` | Database password |
| `RUN_CONTINUOUS` | `0` | Set to `1` for continuous producer mode |
| `PRODUCER_POLL_INTERVAL` | `5` | Seconds between producer polls (continuous mode) |
| `KAFKA_WAIT_TIMEOUT` | `120` | Seconds to wait for Kafka on startup |
| `SOURCE_API_WAIT_TIMEOUT` | `120` | Seconds to wait for source API on startup |

---

## Troubleshooting

### Kafka connector not found (AnalysisException: Failed to find data source: kafka)

The Spark Kafka JAR needs to be downloaded on first run. `main.py` handles this automatically via `spark-submit --packages`. If it fails, trigger the download manually:

```bash
/path/to/spark/bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8 \
  --version
```

JARs are cached in `~/.ivy2/jars/` after the first successful download.

### Address already in use (port 8001 / 8000 / 3000)

A previous run left processes alive. Kill them:

```bash
lsof -ti :8001 | xargs kill -9 2>/dev/null
lsof -ti :8000 | xargs kill -9 2>/dev/null
lsof -ti :3000 | xargs kill -9 2>/dev/null
```

### Batch mode runs instead of streaming

You must pass `--realtime` explicitly:

```bash
python3 main.py --realtime
```

Without it, `main.py` runs the batch pipeline which blocks on `kafka_producer` synchronously.

### stream_silver_gold exits immediately (silver_gold job exited)

This happens when `stream_silver_gold` starts before `stream_to_bronze` has written its first bronze batch. The 30-second startup delay in `main.py` prevents this. If it still occurs, clear the stale checkpoint and retry:

```bash
rm -rf checkpoints/silver_gold_stream
python3 main.py --realtime
```

### ModuleNotFoundError: No module named 'src'

PYTHONPATH is not set. `main.py` sets it automatically. If running scripts directly:

```bash
export PYTHONPATH="$(pwd)"
spark-submit src/etl/batch_to_bronze.py
```

### Spark driver bind error on macOS

Already handled in all Spark job scripts:

```python
.config("spark.driver.bindAddress", "127.0.0.1")
.config("spark.driver.host", "127.0.0.1")
```

### Model or silver layer returns 503

The pipeline hasn't completed yet. Run the full batch pipeline first, or wait for the streaming pipeline to process at least one batch.

---

## Recent Changes

### Codebase cleanup (May 2026)

- **Removed** `src/dashboard/app.py` — orphaned Streamlit dashboard superseded by the Next.js + FastAPI frontend
- **Removed** `notebooks/random_arrays_demo.ipynb` — unrelated demo file
- **Removed** `grocery_etl_pipeline/` — empty leftover directory
- **Extracted** shared model loader into `src/training/model_utils.py` — eliminates the duplicate `get_model()` implementation that existed in both `src/app/main.py` and `src/etl/stream_silver_gold.py`
- **Fixed** streaming pipeline startup race condition — added 30-second delay before launching `stream_silver_gold` so bronze has time to initialize
- **Fixed** Spark Kafka connector — pre-downloaded `spark-sql-kafka-0-10_2.12:3.5.8` JAR to `~/.ivy2/jars/` so streaming jobs start without network dependency

---

*Course project — Data Engineering, Semester 2, 2025–2026*
