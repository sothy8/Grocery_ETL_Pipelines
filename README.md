# 🛒 Grocery Sales End-to-End Data Engineering Pipeline

A complete, production-ready data engineering solution that ingests grocery sales data, performs ETL transformations, trains ML models, and serves predictions via API and interactive dashboard.

**Status:** ✅ Fully Operational | 🧪 Production-Ready | 📊 Live Dashboard

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Dataset](#dataset)
4. [Quick Start](#quick-start)
5. [Components](#components)
6. [API Documentation](#api-documentation)
7. [Dashboard Features](#dashboard-features)
8. [Database Schema](#database-schema)
9. [Troubleshooting](#troubleshooting)
10. [Project Structure](#project-structure)
11. [Technology Stack](#technology-stack)

---

## 🎯 Overview

This project demonstrates a complete end-to-end data pipeline:

- **Data Ingestion**: Dual sources (REST API + Kafka streaming)
- **ETL Pipeline**: Spark-based batch and streaming processing
- **Data Warehouse**: PostgreSQL with star schema (medallion architecture)
- **Machine Learning**: Sales prediction model (RandomForest, R² = 0.581)
- **APIs & Dashboards**: FastAPI prediction service + Streamlit analytics dashboard
- **Infrastructure**: Docker-based services (Kafka, Zookeeper, PostgreSQL)

### Key Metrics
- **Dataset Size**: 8,524 sales records
- **Data Quality**: 1,463 missing weights (17%), mixed categorical labels
- **Model Performance**: R² = 0.581, RMSE = $40.72, MAE = $28.24
- **Warehouse Capacity**: 8,523 facts, 1,559 item dimensions, 16 outlets

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                 │
├─────────────────────────────────────────────────────────────────────┤
│                      grocerySale.csv                                │
│                    (8,524 records, 12 cols)                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                  ▼
    ┌──────────────┐              ┌──────────────────┐
    │ Source API   │              │ Kafka Producer   │
    │ (Port 8001)  │              │ (Streaming)      │
    └──────┬───────┘              └────────┬─────────┘
           │                               │
           │         REST API              │   Kafka Topic
           │         (paginated)           │   (grocery-sales)
           │                               │
           └───────────┬───────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   SPARK ETL PROCESSING       │
        │  ┌────────────────────────┐  │
        │  │  Batch to Bronze       │  │  ◄─── Extract phase
        │  │  (src/etl/extract.py)  │  │
        │  └────────┬───────────────┘  │
        │           │                  │
        │  ┌────────▼───────────────┐  │
        │  │  Silver Processing     │  │  ◄─── Transform phase
        │  │  (src/etl/transform.py)│  │
        │  └────────┬───────────────┘  │
        │           │                  │
        │  ┌────────▼───────────────┐  │
        │  │  Gold Star Schema      │  │  ◄─── Load phase
        │  │  (src/etl/load.py)     │  │
        │  └────────┬───────────────┘  │
        └───────────┼──────────────────┘
                    │
        ┌───────────┼───────────────┐
        │           │               │
        ▼           ▼               ▼
    ┌────────┐ ┌────────┐ ┌──────────────┐
    │ Bronze │ │ Silver │ │ PostgreSQL   │
    │ Parquet│ │Parquet │ │ Data         │
    │        │ │        │ │ Warehouse    │
    └────────┘ └────────┘ │              │
                          │  ✅ 8,523    │
                          │     facts    │
                          │  ✅ 3 dims   │
                          └──────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ ML Training  │ │ FastAPI      │ │ Streamlit    │
        │ (Port 8000)  │ │ (Port 8000)  │ │ (Port 8501)  │
        │              │ │              │ │              │
        │ RandomForest │ │ /predict     │ │ Interactive  │
        │ Model        │ │ /health      │ │ Dashboard    │
        │ joblib       │ │ /summary     │ │ w/ Filters   │
        └──────────────┘ └──────────────┘ └──────────────┘
```

### Data Flow Stages

| Stage | Technology | Input | Output | Purpose |
|-------|-----------|-------|--------|---------|
| **Ingest** | FastAPI + Kafka | CSV | API + Stream | Expose data for consumption |
| **Extract** | PySpark | API/Stream | Raw Parquet | Capture raw data as-is |
| **Transform** | PySpark | Raw Parquet | Cleaned Parquet | Data quality + standardization |
| **Load** | PySpark + SQL | Clean Parquet | PostgreSQL | Enable BI queries |
| **Train** | scikit-learn | Silver Parquet | joblib model | Build predictive model |
| **Serve** | FastAPI | Model | JSON API | Real-time predictions |
| **Visualize** | Streamlit | All Layers | HTML Dashboard | Interactive analytics |

---

## 📊 Dataset

### Source Data (`grocerySale.csv`)
- **Rows**: 8,524 sales transactions
- **Columns**: 12 features
- **Size**: ~830KB

### Data Quality Issues

| Issue | Count | Impact | Fix |
|-------|-------|--------|-----|
| Missing `Item Weight` | 1,463 (17%) | Median imputation | Filled with median |
| Mixed `Fat Content` labels | 3 variants | Inconsistency | Standardized to "Low Fat", "Regular" |
| No timestamp | - | Use ingestion time | Applied to all records |

### Features

**Categorical:**
- `Item Fat Content`: Low Fat, Regular
- `Item Type`: 16 product categories (Fruits, Dairy, Snacks, etc.)
- `Outlet Type`: Supermarket Type1/2/3, Grocery Store
- `Outlet Location Type`: Tier 1, 2, 3 (geographic tier)
- `Outlet Size`: Small, Medium, High

**Numeric:**
- `Item Visibility`: Product shelf visibility [0, 1]
- `Item Weight`: Product weight in kg
- `Outlet Establishment Year`: Year outlet opened
- `Total Sales`: Revenue target variable
- `Rating`: Customer satisfaction [1-5]

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Apache Spark 3.5.8 (local installation)
- macOS or Linux (tested on macOS 15.7.4)

### 1️⃣ Initial Setup (5 minutes)

```bash
# Clone and navigate
cd /path/to/project

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Docker services
docker compose up -d
docker compose ps  # Verify all containers are UP
```

### 2️⃣ Run Full Pipeline (15 minutes total)

**Terminal 1: Data Source**
```bash
source .venv/bin/activate
python -m src.ingest.source_api
# Runs on http://127.0.0.1:8001
```

**Terminal 2: Stream Data**
```bash
source .venv/bin/activate
python -m src.ingest.kafka_producer
# Publishes 8,524 rows to Kafka topic "grocery-sales"
```

**Terminal 3: ETL Pipeline** ⚠️ **IMPORTANT: Set PYTHONPATH**
```bash
source .venv/bin/activate
export PYTHONPATH="$(pwd)"  # ← Required for spark-submit

# Batch ingestion (Bronze layer)
spark-submit src/etl/batch_to_bronze.py
# ✓ Creates data/bronze/ (~156KB)

# Transform & warehouse (Silver + Gold)
spark-submit src/etl/silver_gold.py
# ✓ Creates data/silver/ + data/gold/ star schema
```

**Terminal 4: Training & Loading**
```bash
source .venv/bin/activate

# Train ML model
python -m src.training.train_model
# ✓ Creates models/grocery_sales_model.joblib

# Load warehouse
python -m src.warehouse.load_gold_to_postgres
# ✓ Populates PostgreSQL tables
```

**Terminal 5: Prediction API**
```bash
source .venv/bin/activate
uvicorn src.app.main:app --reload
# ✓ Runs on http://127.0.0.1:8000
# ✓ Interactive docs: http://127.0.0.1:8000/docs
```

**Terminal 6: Analytics Dashboard**
```bash
source .venv/bin/activate
streamlit run src/dashboard/app.py
# ✓ Runs on http://127.0.0.1:8501
# ✓ Interactive filters + 10+ visualizations
```

---

## 🔧 Components

### Data Ingestion Layer

#### `src/ingest/source_api.py`
REST API exposing CSV as JSON with pagination
- **Endpoint**: `GET /data?limit=100&offset=0`
- **Health Check**: `GET /health` → `{"status": "ok"}`
- **Port**: 8001
- **Use Case**: Simulate real-time data sources

#### `src/ingest/kafka_producer.py`
Streams data from API to Kafka topic
- **Topic**: `grocery-sales`
- **Rate**: 0.01s delay per record (realistic throttling)
- **Format**: JSON per row
- **Brokers**: `localhost:9092`

### ETL Layer

#### Modular Architecture: Extract → Transform → Load

**`src/etl/extract.py`**
- `extract_batch_csv(spark)` → Parquet with schema inference
- `extract_stream_kafka(spark)` → Kafka streaming dataframe

**`src/etl/transform.py`**
- `clean_frame(df)` → Rename, normalize fat content, trim strings
- `add_imputed_weight(df)` → Fill nulls with median
- `build_gold_layers(df)` → Create star schema tables

**`src/etl/load.py`**
- `load_to_bronze(df, path)` → Write raw data
- `load_to_silver(df, path)` → Write cleaned data
- `load_to_gold(gold_dict, path)` → Write dimension + fact tables

#### Orchestrators

**`src/etl/batch_to_bronze.py`**
- Reads: `grocerySale.csv`
- Writes: `data/bronze/` (Parquet)
- Spark Config: `driver.bindAddress=127.0.0.1`

**`src/etl/silver_gold.py`**
- Reads: `data/bronze/` (Parquet)
- Writes: `data/silver/` + `data/gold/{dim_item,dim_outlet,dim_date,fact_sales}/`
- Transformations: Cleaning, imputation, star schema build

### Warehouse Layer

#### `src/warehouse/star_schema.sql`
PostgreSQL DDL defining:
- `grocery_schema.fact_sales` (8,523 rows)
  - Surrogate key, 3 FKs, measures, timestamp
- `grocery_schema.dim_item` (1,559 rows)
  - Product attributes, surrogate key
- `grocery_schema.dim_outlet` (16 rows)
  - Store attributes, surrogate key
- `grocery_schema.dim_date` (1 row)
  - Ingestion date, surrogate key

#### `src/warehouse/load_gold_to_postgres.py`
- Executes DDL from `star_schema.sql`
- Reads Parquet from `data/gold/`
- Appends to PostgreSQL tables
- Connection: `postgresql://grocery:grocery@localhost:5432/grocery_warehouse`

### ML Training Layer

#### `src/training/train_model.py`
**Algorithm**: RandomForestRegressor (200 trees)

**Input**: `data/silver/` (cleaned data)

**Pipeline**:
1. OneHotEncoder for categorical features
2. Passthrough for numeric features
3. RandomForest with `n_jobs=-1` (parallel)

**Output**:
- Model: `models/grocery_sales_model.joblib` (117MB)
- Metrics: `models/metrics.json`
  ```json
  {
    "mae": 28.24,
    "rmse": 40.72,
    "r2": 0.581
  }
  ```

**Test Split**: 80/20 stratified

### Serving Layer

#### `src/app/main.py` - FastAPI Prediction Service

**Base URL**: `http://127.0.0.1:8000`

**Endpoints**:

| Method | Path | Description | Returns |
|--------|------|-------------|---------|
| `GET` | `/` | API info | Links to all endpoints |
| `GET` | `/health` | Health check | `{"status": "ok"}` |
| `GET` | `/summary` | Data statistics | Row count, columns, avg/sum sales |
| `GET` | `/sample-payload` | Example request | JSON request template |
| `POST` | `/predict` | Make prediction | `{"predicted_total_sales": <float>}` |
| `GET` | `/docs` | Swagger UI | Interactive API explorer |

**Request Example**:
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

**Response**:
```json
{
  "predicted_total_sales": 125.23
}
```

### Analytics Layer

#### `src/dashboard/app.py` - Streamlit Dashboard

**URL**: `http://127.0.0.1:8501`

**Features**:
- ✅ 6 advanced sidebar filters (item type, outlet, location, size, fat content, sales range)
- ✅ 5 KPI metrics with delta indicators
- ✅ 10+ professional Plotly visualizations
- ✅ Data explorer with 3 tabs (table, stats, samples)
- ✅ Top 10 products ranking
- ✅ Warehouse preview (Gold layer)
- ✅ Real-time filtering across all charts

---

## 📡 API Documentation

### Health Check
```
GET /health
```
**Response**: `200 OK`
```json
{"status": "ok"}
```

### Data Summary
```
GET /summary
```
**Response**: `200 OK`
```json
{
  "rows": 8523,
  "columns": ["item_fat_content", "item_type", ...],
  "total_sales_mean": 140.99,
  "total_sales_sum": 1201681.48
}
```

### Make Prediction
```
POST /predict
Content-Type: application/json

{
  "item_fat_content": "Low Fat",
  "item_type": "Fruits and Vegetables",
  "outlet_location_type": "Tier 1",
  "outlet_size": "Medium",
  "outlet_type": "Supermarket Type1",
  "outlet_establishment_year": 2012,
  "item_visibility": 0.1,
  "item_weight": 15.1
}
```

**Response**: `200 OK`
```json
{"predicted_total_sales": 125.23}
```

**Error Handling**:
- `503 Service Unavailable`: Model or Silver layer missing
- `422 Unprocessable Entity`: Invalid request format

---

## 📊 Dashboard Features

### Sidebar Filters (Real-time)
- **Item Type**: Multi-select from 16 categories
- **Outlet Type**: Multi-select (Supermarket, Grocery)
- **Location Type**: Multi-select by tier (1, 2, 3)
- **Outlet Size**: Multi-select (Small, Medium, High)
- **Fat Content**: Multi-select (Low Fat, Regular)
- **Sales Range**: Slider min-max filter
- **Reset Button**: Clear all filters instantly
- **Record Counter**: Shows filtered vs total records

### Key Performance Indicators
- Total Records (with Δ from original)
- Average Sales ($)
- Total Sales ($)
- Average Rating (⭐)
- Model R² Score

### Visualizations
1. **Sales by Item Type** - Colored bar chart
2. **Outlet Distribution** - Pie chart
3. **Sales Distribution** - Histogram
4. **Location Performance** - Horizontal bar
5. **Box Plot** - Sales variance by outlet size
6. **Fat Content Analysis** - Category performance
7. **Outlet Age Trend** - Line chart over years
8. **Top 10 Products** - Ranked table
9. **Gold Layer Preview** - Warehouse sample

### Data Explorer Tabs

**📊 Data Table**
- Sortable table with all columns
- Display 10/25/50/100/all rows
- Sort by any column
- Formatted currency, decimals, ratings

**📈 Column Statistics**
- Min, max, mean, std, quartiles
- Categorical distribution pie chart
- Switch between categories

**🔍 Sample Records**
- Random samples (5-50 records)
- Summary metrics
- Formatted display

---

## 🗄️ Database Schema

### PostgreSQL Connection
```
Host: localhost
Port: 5432
User: grocery
Password: grocery
Database: grocery_warehouse
Schema: grocery
```

### Tables

#### fact_sales (8,523 rows)
```sql
CREATE TABLE grocery.fact_sales (
  item_key VARCHAR PRIMARY KEY,
  outlet_key VARCHAR FOREIGN KEY REFERENCES dim_outlet,
  date_key VARCHAR FOREIGN KEY REFERENCES dim_date,
  item_visibility DOUBLE,
  item_weight DOUBLE NOT NULL,
  total_sales DOUBLE,
  rating DOUBLE,
  ingest_ts TIMESTAMP
);
```

#### dim_item (1,559 rows)
```sql
CREATE TABLE grocery.dim_item (
  item_key VARCHAR PRIMARY KEY,
  item_identifier VARCHAR,
  item_type VARCHAR,
  item_fat_content VARCHAR
);
```

#### dim_outlet (16 rows)
```sql
CREATE TABLE grocery.dim_outlet (
  outlet_key VARCHAR PRIMARY KEY,
  outlet_identifier VARCHAR,
  outlet_type VARCHAR,
  outlet_location_type VARCHAR,
  outlet_size VARCHAR,
  outlet_establishment_year INTEGER
);
```

#### dim_date (1 row)
```sql
CREATE TABLE grocery.dim_date (
  date_key VARCHAR PRIMARY KEY,
  ingest_date DATE
);
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
**Cause**: PYTHONPATH not set for spark-submit
**Fix**:
```bash
export PYTHONPATH="$(pwd)"
spark-submit src/etl/batch_to_bronze.py
```

### "BindException: Can't assign requested address"
**Cause**: Spark driver port binding failure on macOS
**Fix**: Already configured in ETL scripts
```python
.config("spark.driver.bindAddress", "127.0.0.1")
```

### "ConnectionRefusedError" on Kafka
**Cause**: Kafka container not running
**Fix**:
```bash
docker compose up -d kafka zookeeper
docker compose logs kafka
```

### "ModuleNotFoundError: No module named 'joblib'"
**Cause**: Dependencies not installed
**Fix**:
```bash
source .venv/bin/activate
pip install joblib scikit-learn
```

### "ERROR: Operation cancelled by user" on pip install
**Cause**: Large package installation timeout
**Fix**: Install packages individually:
```bash
pip install scikit-learn
pip install streamlit
pip install plotly
```

### Dashboard won't load filters
**Cause**: Streamlit cache issue
**Fix**: Clear cache and restart
```bash
streamlit cache clear
streamlit run src/dashboard/app.py
```

---

## 📁 Project Structure

```
Course_Project/
├── grocerySale.csv                 # Source data (8,524 rows)
├── .venv/                          # Python virtual environment
├── docker-compose.yml              # Kafka, Zookeeper, PostgreSQL
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── data/                           # Data lake (Parquet files)
│   ├── bronze/                     # Raw data
│   ├── silver/                     # Cleaned data
│   └── gold/                       # Star schema
│       ├── fact_sales/
│       ├── dim_item/
│       ├── dim_outlet/
│       └── dim_date/
│
├── models/                         # ML artifacts
│   ├── grocery_sales_model.joblib  # Trained RandomForest
│   └── metrics.json                # Model evaluation
│
├── src/
│   ├── ingest/                     # Data ingestion
│   │   ├── source_api.py          # REST API (port 8001)
│   │   └── kafka_producer.py      # Kafka producer
│   │
│   ├── etl/                        # ETL pipeline
│   │   ├── extract.py             # Extraction layer
│   │   ├── transform.py           # Transformation layer
│   │   ├── load.py                # Load layer
│   │   ├── batch_to_bronze.py     # Batch orchestrator
│   │   ├── stream_to_bronze.py    # Stream orchestrator
│   │   └── silver_gold.py         # Transform & warehouse
│   │
│   ├── warehouse/                  # Data warehouse
│   │   ├── star_schema.sql        # DDL
│   │   └── load_gold_to_postgres.py # Warehouse loader
│   │
│   ├── training/                   # ML training
│   │   └── train_model.py         # RandomForest trainer
│   │
│   ├── app/                        # Serving layer
│   │   └── main.py                # FastAPI (port 8000)
│   │
│   ├── dashboard/                  # Analytics
│   │   └── app.py                 # Streamlit (port 8501)
│   │
│   └── config.py                  # Configuration (paths, credentials)
```

---

## 🛠️ Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Data Processing** | Apache Spark | 3.5.8 | Batch/stream ETL |
| **Message Queue** | Apache Kafka | 7.6.1 | Event streaming |
| **Database** | PostgreSQL | 16 | OLAP warehouse |
| **Python Runtime** | Python | 3.12 | Application runtime |
| **Data Formats** | Parquet | - | Columnar storage |
| **ML Framework** | scikit-learn | 1.8.0 | Predictive modeling |
| **Web API** | FastAPI | 0.136.1 | REST endpoints |
| **Analytics UI** | Streamlit | 1.57.0 | Interactive dashboard |
| **Visualization** | Plotly | 5.24.1 | Interactive charts |
| **Orchestration** | Docker Compose | - | Infrastructure |
| **Model Storage** | joblib | 1.5.3 | Serialization |
| **ORM** | SQLAlchemy | - | Database abstraction |

---

## ✅ Validation Checklist

- [x] Source API running and serving data
- [x] Kafka producer streaming records
- [x] Bronze layer created (8,524 records)
- [x] Silver layer created (cleaned, imputed)
- [x] Gold star schema created (facts + dimensions)
- [x] PostgreSQL loaded (8,523 facts)
- [x] ML model trained (R² = 0.581)
- [x] FastAPI predictions working
- [x] Streamlit dashboard interactive
- [x] All filters functional
- [x] Visualizations rendering
- [x] Data explorer tabs working

---

## 📝 License & Attribution

This is a course project for Data Engineering (Semester 2, 2025-2026).

---

## 🎓 Learning Objectives Achieved

✅ End-to-end data pipeline design and implementation
✅ ETL orchestration with Apache Spark
✅ Real-time streaming with Apache Kafka
✅ Data warehouse modeling (star schema)
✅ Machine learning model training and deployment
✅ REST API development (FastAPI)
✅ Interactive analytics (Streamlit)
✅ Docker-based infrastructure
✅ Data quality handling (nulls, inconsistencies)
✅ Production-ready Python code structure

---

**Last Updated**: May 2, 2026
**Status**: ✅ Production Ready
# Grocery_ETL_Pipelines
