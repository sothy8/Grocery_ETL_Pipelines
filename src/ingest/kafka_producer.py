from __future__ import annotations

import json
import os
import time
from typing import Any

import requests
from kafka import KafkaProducer

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

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda value: value.encode("utf-8") if value else None,
        acks="all",
        retries=5,
    )

    rows = fetch_rows(api_url)
    for row in rows:
        key = str(row.get("Item Identifier", "unknown"))
        producer.send(topic, key=key, value=row)
        time.sleep(0.01)

    producer.flush()
    producer.close()


if __name__ == "__main__":
    main()
