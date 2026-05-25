from __future__ import annotations

import json
import os
import time
from typing import Any

import requests
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from src.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, SOURCE_API_URL


def fetch_rows(api_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    page_size = 1000

    while True:
        response = requests.get(f"{api_url}/sales?limit={page_size}&offset={offset}", timeout=30)
        response.raise_for_status()
        payload = response.json()
        batch = payload["data"]
        if not batch:
            break
        rows.extend(batch)
        offset += page_size

    return rows


def main() -> None:
    api_url = os.getenv("SOURCE_API_URL", SOURCE_API_URL)
    topic = os.getenv("KAFKA_TOPIC", KAFKA_TOPIC)
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", KAFKA_BOOTSTRAP_SERVERS)
    continuous = os.getenv("RUN_CONTINUOUS", "0") in ("1", "true", "True")

    # Attempt to connect to Kafka with retries to tolerate broker startup delays
    attempts = int(os.getenv("PRODUCER_BOOTSTRAP_RETRY_ATTEMPTS", "60"))
    interval = int(os.getenv("PRODUCER_BOOTSTRAP_RETRY_INTERVAL", "2"))
    producer = None
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda value: value.encode("utf-8") if value else None,
                acks="all",
                retries=5,
            )
            break
        except NoBrokersAvailable as exc:
            last_exc = exc
            print(f"Kafka broker not available (attempt {attempt}/{attempts}), retrying in {interval}s...")
            time.sleep(interval)
        except Exception as exc:
            last_exc = exc
            print(f"Unexpected error creating KafkaProducer: {exc}")
            time.sleep(interval)

    if producer is None:
        print("Failed to connect to Kafka after retries; exiting.")
        if last_exc:
            raise last_exc
        raise SystemExit(1)

    try:
        while True:
            rows = fetch_rows(api_url)
            for row in rows:
                key = str(row.get("Item Identifier", "unknown"))
                producer.send(topic, key=key, value=row)
                # small sleep to avoid tiny bursts
                time.sleep(0.01)

            producer.flush()

            if not continuous:
                break

            # continuous mode: wait then poll API again for new rows
            time.sleep(int(os.getenv("PRODUCER_POLL_INTERVAL", "5")))
    finally:
        try:
            producer.flush()
            producer.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
