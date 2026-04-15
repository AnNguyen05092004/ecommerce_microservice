#!/usr/bin/env python3
"""Seed categories and products for newly added product services.

Targets 9 newly added services:
- tablet, audio, wearable
- component, peripheral, monitor
- accessory, charging, book

Usage:
  python scripts/seed_new_product_services.py

Requirements:
- docker compose stack is running
- staff account exists (manager_test/Manager@123 by default)
"""

from __future__ import annotations

import json
import os
import time
from urllib import error, request

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000").rstrip("/")
STAFF_USERNAME = os.environ.get("SEED_STAFF_USERNAME", "manager_test")
STAFF_PASSWORD = os.environ.get("SEED_STAFF_PASSWORD", "Manager@123")
TIMEOUT = 15

SERVICE_CONFIGS = [
    {
        "type": "tablet",
        "service": "tablet-service",
        "resource": "tablets",
        "categories": ["Tablet học tập", "Tablet giải trí", "Tablet cao cấp"],
    },
    {
        "type": "audio",
        "service": "audio-service",
        "resource": "audios",
        "categories": ["Tai nghe TWS", "Tai nghe chụp tai", "Loa Bluetooth"],
    },
    {
        "type": "wearable",
        "service": "wearable-service",
        "resource": "wearables",
        "categories": ["Smartwatch phổ thông", "Smartwatch thể thao", "Smartband"],
    },
    {
        "type": "component",
        "service": "component-service",
        "resource": "components",
        "categories": ["CPU", "RAM", "SSD"],
    },
    {
        "type": "peripheral",
        "service": "peripheral-service",
        "resource": "peripherals",
        "categories": ["Bàn phím", "Chuột", "Webcam"],
    },
    {
        "type": "monitor",
        "service": "monitor-service",
        "resource": "monitors",
        "categories": ["Màn hình văn phòng", "Màn hình gaming", "Màn hình đồ họa"],
    },
    {
        "type": "accessory",
        "service": "accessory-service",
        "resource": "accessories",
        "categories": ["Ốp lưng", "Kính cường lực", "Cáp dữ liệu"],
    },
    {
        "type": "charging",
        "service": "charging-service",
        "resource": "chargings",
        "categories": ["Củ sạc nhanh", "Pin dự phòng", "Sạc không dây"],
    },
    {
        "type": "book",
        "service": "book-service",
        "resource": "books",
        "categories": ["Sách lập trình", "Sách công nghệ", "Sách kỹ năng số"],
    },
]

BRANDS = {
    "tablet": ["Apple", "Samsung", "Xiaomi"],
    "audio": ["Sony", "JBL", "Anker"],
    "wearable": ["Apple", "Garmin", "Amazfit"],
    "component": ["Intel", "AMD", "Kingston"],
    "peripheral": ["Logitech", "Razer", "Rapoo"],
    "monitor": ["Dell", "LG", "ASUS"],
    "accessory": ["Spigen", "Baseus", "Ugreen"],
    "charging": ["Anker", "Baseus", "Belkin"],
    "book": ["NXB Trẻ", "O'Reilly", "Wiley"],
}


def log(message: str) -> None:
    print(message, flush=True)


def http_json(method: str, path: str, data=None, token: str = ""):
    url = f"{GATEWAY_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = request.Request(url=url, data=body, method=method.upper(), headers=headers)

    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return resp.status, payload
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw}
        return exc.code, payload


def wait_for_gateway(max_wait: int = 60) -> None:
    started = time.time()
    while time.time() - started < max_wait:
        status, _ = http_json("GET", "/health")
        if status == 200:
            return
        time.sleep(2)
    raise RuntimeError("Gateway is not ready")


def login_staff() -> str:
    status, payload = http_json(
        "POST",
        "/api/staff-service/auth/login/",
        {"username": STAFF_USERNAME, "password": STAFF_PASSWORD},
    )
    if status != 200:
        raise RuntimeError(
            "Staff login failed. Run scripts/seed_test_data.py first to bootstrap accounts. "
            f"HTTP {status} {payload}"
        )
    token = payload.get("token", "")
    if not token:
        raise RuntimeError("Staff login returned no token")
    return token


def ensure_categories(service: str, names: list[str], token: str) -> list[int]:
    status, payload = http_json("GET", f"/api/{service}/categories/")
    if status != 200:
        raise RuntimeError(f"Cannot list categories for {service}: {status} {payload}")

    existing = {}
    if isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                n = row.get("name")
                i = row.get("id")
                if isinstance(n, str) and isinstance(i, int):
                    existing[n] = i

    for name in names:
        if name in existing:
            continue
        c_status, c_payload = http_json(
            "POST",
            f"/api/{service}/categories/",
            {"name": name, "description": f"Danh mục {name}"},
            token=token,
        )
        if c_status != 201:
            raise RuntimeError(
                f"Create category failed for {service}: {c_status} {c_payload}"
            )
        existing[name] = c_payload.get("id")

    return [existing[n] for n in names if n in existing]


def get_existing_product_names(service: str, resource: str) -> set[str]:
    status, payload = http_json("GET", f"/api/{service}/{resource}/?page_size=500")
    if status != 200:
        raise RuntimeError(f"Cannot list products for {service}: {status} {payload}")

    rows = payload.get("results", []) if isinstance(payload, dict) else payload
    names: set[str] = set()
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                names.add(row["name"])
    return names


def build_products(ptype: str, category_ids: list[int]) -> list[dict]:
    brands = BRANDS.get(ptype, ["TechStore"])
    rows = []
    for idx in range(1, 13):
        category_id = category_ids[(idx - 1) % len(category_ids)] if category_ids else 1
        price = 1500000 + idx * 350000
        rows.append(
            {
                "name": f"{ptype.title()} Product {idx}",
                "brand": brands[(idx - 1) % len(brands)],
                "price": price,
                "description": f"{ptype.title()} model {idx} cho nhu cầu phổ thông và nâng cao.",
                "image": "https://images.unsplash.com/photo-1527443224154-c4e38a8d6d58?auto=format&fit=crop&w=1200&q=80",
                "stock": 40 + idx,
                "category_id": category_id,
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "N/A",
                    "os": "N/A",
                },
            }
        )
    return rows


def seed_service(config: dict, token: str) -> tuple[int, int]:
    service = config["service"]
    resource = config["resource"]
    ptype = config["type"]

    category_ids = ensure_categories(service, config["categories"], token)
    existing_names = get_existing_product_names(service, resource)

    created = 0
    skipped = 0
    for product in build_products(ptype, category_ids):
        if product["name"] in existing_names:
            skipped += 1
            continue
        status, payload = http_json(
            "POST",
            f"/api/{service}/{resource}/",
            product,
            token=token,
        )
        if status != 201:
            raise RuntimeError(
                f"Create product failed for {service}: {status} {payload}"
            )
        created += 1

    return created, skipped


def main() -> int:
    wait_for_gateway()
    token = login_staff()

    total_created = 0
    total_skipped = 0

    for config in SERVICE_CONFIGS:
        created, skipped = seed_service(config, token)
        total_created += created
        total_skipped += skipped
        log(f"{config['service']}: created={created}, skipped_existing={skipped}")

    log(f"Done. total_created={total_created}, total_skipped_existing={total_skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
