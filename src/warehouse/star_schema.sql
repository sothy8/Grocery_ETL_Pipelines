CREATE SCHEMA IF NOT EXISTS grocery;

CREATE TABLE IF NOT EXISTS grocery.dim_item (
    item_key TEXT PRIMARY KEY,
    item_identifier TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_fat_content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grocery.dim_outlet (
    outlet_key TEXT PRIMARY KEY,
    outlet_identifier TEXT NOT NULL,
    outlet_location_type TEXT NOT NULL,
    outlet_size TEXT NOT NULL,
    outlet_type TEXT NOT NULL,
    outlet_establishment_year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS grocery.dim_date (
    date_key TEXT PRIMARY KEY,
    event_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS grocery.fact_sales (
    sales_id BIGSERIAL PRIMARY KEY,
    item_key TEXT NOT NULL REFERENCES grocery.dim_item(item_key),
    outlet_key TEXT NOT NULL REFERENCES grocery.dim_outlet(outlet_key),
    date_key TEXT NOT NULL REFERENCES grocery.dim_date(date_key),
    item_visibility DOUBLE PRECISION,
    item_weight DOUBLE PRECISION,
    total_sales DOUBLE PRECISION,
    rating DOUBLE PRECISION,
    ingest_ts TIMESTAMP
);
