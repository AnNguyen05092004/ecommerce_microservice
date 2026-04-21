#!/usr/bin/env python3
"""Seed test data for TechStore microservices.

Creates/updates:
- 1 customer account
- 1 staff account
- 1 manager account (mapped to role=admin in staff-service)
- categories for laptop/mobile/clothes + extended product groups
- 30 laptops
- 30 mobiles
- 50 clothes
- curated products for tablet/audio/wearable/component/peripheral/monitor/accessory/charging/book
- optional cart items for the seeded customer

Usage:
  python scripts/seed_test_data.py

Requirements:
- docker compose stack is running
- gateway available at http://localhost:8000 (or set GATEWAY_URL)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT_DIR = Path(__file__).resolve().parents[1]
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 15
SEED_CART = os.environ.get("SEED_CART", "false").lower() in ("1", "true", "yes")
SEED_CUSTOMERS_ORDERS = os.environ.get("SEED_CUSTOMERS_ORDERS", "true").lower() in (
    "1",
    "true",
    "yes",
)
SEED_EXTENDED_PRODUCTS = os.environ.get("SEED_EXTENDED_PRODUCTS", "true").lower() in (
    "1",
    "true",
    "yes",
)
RESET_PRODUCT_CATALOG = os.environ.get("RESET_PRODUCT_CATALOG", "false").lower() in (
    "1",
    "true",
    "yes",
)

ACCOUNTS = {
    "manager": {
        "username": "manager_test",
        "password": "Manager@123",
        "full_name": "Manager Test",
        "email": "manager_test@techstore.local",
        "phone": "0900000001",
        "role": "admin",  # manager maps to admin role in current staff-service
    },
    "staff": {
        "username": "staff_test",
        "password": "Staff@123",
        "full_name": "Staff Test",
        "email": "staff_test@techstore.local",
        "phone": "0900000002",
        "role": "staff",
    },
    "customer": {
        "username": "customer_test",
        "password": "Customer@123",
        "full_name": "Customer Test",
        "email": "customer_test@techstore.local",
        "phone": "0900000003",
        "address": "Ho Chi Minh City",
    },
}


def log(message: str) -> None:
    print(message, flush=True)


def run_compose_exec(service: str, code: str) -> None:
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        service,
        "python",
        "manage.py",
        "shell",
        "-c",
        code,
    ]
    result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"docker compose exec failed for {service}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def http_json(
    method: str, path: str, data: Any | None = None, token: str = ""
) -> tuple[int, Any]:
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
    start = time.time()
    while time.time() - start < max_wait:
        status, _ = http_json("GET", "/health")
        if status == 200:
            log("Gateway is healthy.")
            return
        time.sleep(2)
    raise RuntimeError("Gateway is not reachable at /health")


def bootstrap_accounts_direct_db() -> None:
    log("Bootstrapping manager/staff/customer accounts directly in service DBs...")

    manager = ACCOUNTS["manager"]
    staff = ACCOUNTS["staff"]
    customer = ACCOUNTS["customer"]

    staff_code = f"""
from staff.models import Staff

def upsert(username, full_name, email, phone, role, password):
    obj, _ = Staff.objects.get_or_create(username=username, defaults={{
        'full_name': full_name,
        'email': email,
        'phone': phone,
        'role': role,
        'is_active': True,
    }})
    obj.full_name = full_name
    obj.email = email
    obj.phone = phone
    obj.role = role
    obj.is_active = True
    obj.set_password(password)
    obj.save()

upsert('{manager['username']}', '{manager['full_name']}', '{manager['email']}', '{manager['phone']}', '{manager['role']}', '{manager['password']}')
upsert('{staff['username']}', '{staff['full_name']}', '{staff['email']}', '{staff['phone']}', '{staff['role']}', '{staff['password']}')
print('OK')
""".strip()

    customer_code = f"""
from customers.models import Customer

def upsert(username, full_name, email, phone, address, password):
    obj, _ = Customer.objects.get_or_create(username=username, defaults={{
        'full_name': full_name,
        'email': email,
        'phone': phone,
        'address': address,
    }})
    obj.full_name = full_name
    obj.email = email
    obj.phone = phone
    obj.address = address
    obj.set_password(password)
    obj.save()

upsert('{customer['username']}', '{customer['full_name']}', '{customer['email']}', '{customer['phone']}', '{customer['address']}', '{customer['password']}')
print('OK')
""".strip()

    run_compose_exec("staff-service", staff_code)
    run_compose_exec("customer-service", customer_code)


def login_staff(username: str, password: str) -> str:
    status, payload = http_json(
        "POST",
        "/api/staff-service/auth/login/",
        {"username": username, "password": password},
    )
    if status != 200:
        raise RuntimeError(f"Staff login failed: HTTP {status} -> {payload}")
    token = payload.get("token", "")
    if not token:
        raise RuntimeError("Staff login succeeded but no token returned")
    return token


def login_customer(username: str, password: str) -> str:
    status, payload = http_json(
        "POST",
        "/api/customer-service/auth/login/",
        {"username": username, "password": password},
    )
    if status != 200:
        raise RuntimeError(f"Customer login failed: HTTP {status} -> {payload}")
    token = payload.get("token", "")
    if not token:
        raise RuntimeError("Customer login succeeded but no token returned")
    return token


def ensure_categories(token: str) -> tuple[list[int], list[int], list[int]]:
    laptop_categories = [
        ("Ultrabook", "Laptop nhe, pin tot"),
        ("Gaming Laptop", "Hieu nang cao cho gaming"),
        ("Business Laptop", "On dinh cho cong viec"),
    ]
    mobile_categories = [
        ("Flagship", "Dong cao cap"),
        ("Midrange", "Tam trung"),
        ("Budget", "Gia tot"),
    ]
    clothes_categories = [
        ("Áo thun", "Ao thun nam nu"),
        ("Áo sơ mi", "Ao so mi cong so"),
        ("Quần jean", "Quan jean thoi trang"),
        ("Quần short", "Quan short nam nu"),
        ("Váy đầm", "Vay dam nu"),
        ("Áo khoác", "Ao khoac gio mua dong"),
    ]

    status, payload = http_json("GET", "/api/catalog/categories/")
    if status != 200:
        raise RuntimeError(f"Cannot list catalog categories: {status} {payload}")

    existing = {c.get("name"): c.get("id") for c in payload if isinstance(c, dict)}

    all_categories = laptop_categories + mobile_categories + clothes_categories
    for name, desc in all_categories:
        if name in existing:
            continue

        c_status, c_payload = http_json(
            "POST",
            "/api/catalog/categories/",
            {"name": name, "description": desc},
            token=token,
        )
        if c_status not in (200, 201):
            raise RuntimeError(
                f"Create category '{name}' failed: HTTP {c_status} -> {c_payload}"
            )
        existing[name] = c_payload.get("id")

    return (
        [existing[name] for name, _ in laptop_categories if existing.get(name)],
        [existing[name] for name, _ in mobile_categories if existing.get(name)],
        [existing[name] for name, _ in clothes_categories if existing.get(name)],
    )


def get_existing_names(path: str) -> dict[str, int]:
    status, payload = http_json("GET", path)
    if status != 200:
        raise RuntimeError(f"Cannot list items at {path}: {status} {payload}")
    results = payload.get("results", []) if isinstance(payload, dict) else payload
    names: dict[str, int] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        item_id = item.get("id")
        if isinstance(name, str) and isinstance(item_id, int):
            names[name] = item_id
    return names


COMPUTER_SPEC_LIMITS = {
    "cpu": 100,
    "ram": 50,
    "storage": 100,
    "gpu": 100,
    "screen_size": 20,
    "os": 50,
}

MOBILE_SPEC_LIMITS = {
    "screen_size": 20,
    "battery": 50,
    "camera": 100,
    "storage": 50,
    "ram": 50,
    "os": 50,
}


def normalize_specs(specs: dict[str, str], limits: dict[str, int]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, max_len in limits.items():
        value = str(specs.get(key, ""))
        normalized[key] = value[:max_len]
    return normalized


def ensure_30_laptops(token: str, category_ids: list[int]) -> list[int]:
    laptops = [
        {
            "name": "MacBook Pro 16 M3 Max",
            "price": 75000000,
            "description": "Apple MacBook Pro 16-inch M3 Max, Liquid Retina XDR display, professional workstation",
            "image": "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Apple M3 Max",
                "ram": "36GB",
                "storage": "1TB SSD",
                "gpu": "40-core GPU",
                "screen_size": "16 inch",
                "os": "macOS Sonoma",
            },
        },
        {
            "name": "Dell XPS 15 OLED",
            "price": 65000000,
            "description": "Dell XPS 15 with OLED display, RTX 4090 Ada, Intel Core i9 13th gen",
            "image": "https://images.unsplash.com/photo-1588872657840-18491dbba735?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900H",
                "ram": "32GB DDR5",
                "storage": "1TB SSD",
                "gpu": "NVIDIA RTX 4090",
                "screen_size": "15.6 inch OLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "Lenovo ThinkPad X1 Carbon",
            "price": 45000000,
            "description": "Premium business laptop, lightweight, excellent keyboard, long battery life",
            "image": "https://images.unsplash.com/photo-1579509255331-f5a5f8d3f84e?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1365U",
                "ram": "16GB LPDDR5",
                "storage": "512GB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "14 inch FHD",
                "os": "Windows 11 Pro",
            },
        },
        {
            "name": "ASUS ROG Zephyrus G14",
            "price": 55000000,
            "description": "Gaming laptop with RTX 4060, AMD Ryzen 9, portable performance beast",
            "image": "https://images.unsplash.com/photo-1599298881114-e3519c4da82a?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "AMD Ryzen 9 7940HS",
                "ram": "32GB GDDR5",
                "storage": "1TB SSD",
                "gpu": "NVIDIA RTX 4060",
                "screen_size": "14 inch 2.8K",
                "os": "Windows 11",
            },
        },
        {
            "name": "HP Spectre x360 14",
            "price": 52000000,
            "description": "2-in-1 convertible laptop, gorgeous OLED touchscreen, sleek design",
            "image": "https://images.unsplash.com/photo-1611532736579-6b16e2b50449?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1360P",
                "ram": "16GB LPDDR5",
                "storage": "512GB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "14 inch OLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "Acer Swift 5 SF514",
            "price": 38000000,
            "description": "Ultraslim laptop, super lightweight, true 1080p display, great value",
            "image": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i5-1335U",
                "ram": "8GB LPDDR5",
                "storage": "512GB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "14 inch FHD",
                "os": "Windows 11",
            },
        },
        {
            "name": "MSI GS66 Stealth",
            "price": 58000000,
            "description": "Performance gaming laptop, RTX 4080, 16-inch display, ultra-slim design",
            "image": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900HX",
                "ram": "32GB DDR5",
                "storage": "2TB NVMe SSD",
                "gpu": "NVIDIA RTX 4080",
                "screen_size": "16 inch QHD",
                "os": "Windows 11",
            },
        },
        {
            "name": "Razer Blade 16",
            "price": 72000000,
            "description": "Professional gaming laptop, RTX 4090, aluminum unibody, creator-grade display",
            "image": "https://images.unsplash.com/photo-1623974349355-3a35ee0e31ce?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900HX",
                "ram": "32GB DDR5",
                "storage": "2TB SSD",
                "gpu": "NVIDIA RTX 4090",
                "screen_size": "16 inch 4K OLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "LG Gram 17 OLED",
            "price": 48000000,
            "description": "Ultra-premium lightweight laptop, LG OLED display, minimal bezels, 15h battery",
            "image": "https://images.unsplash.com/photo-1602394247121-94bada270032?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1365U",
                "ram": "16GB LPDDR5",
                "storage": "512GB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "17 inch OLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "Framework Laptop 16",
            "price": 42000000,
            "description": "Repairable modular laptop, expandable ports, sustainable design, Intel 13th gen",
            "image": "https://images.unsplash.com/photo-1580522454770-7148bbb1c43d?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1360P",
                "ram": "32GB DDR5",
                "storage": "1TB SSD",
                "gpu": "Intel Arc A750M",
                "screen_size": "16 inch 2.5K",
                "os": "Windows 11",
            },
        },
        {
            "name": "MacBook Air M2",
            "price": 45000000,
            "description": "Thin and light, M2 chip, exceptional battery life, perfect for students",
            "image": "https://images.unsplash.com/photo-1532012197267-da84d127e765?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Apple M2",
                "ram": "16GB",
                "storage": "512GB SSD",
                "gpu": "10-core GPU",
                "screen_size": "13 inch Liquid Retina",
                "os": "macOS Sonoma",
            },
        },
        {
            "name": "ROG Ally Gaming Laptop",
            "price": 34000000,
            "description": "Budget gaming option, RTX 4050, AMD Ryzen 7, portable gaming experience",
            "image": "https://images.unsplash.com/photo-1600298881114-e3519c4da82a?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "AMD Ryzen 7 7735U",
                "ram": "16GB DDR5",
                "storage": "512GB SSD",
                "gpu": "NVIDIA RTX 4050",
                "screen_size": "15.6 inch IPS",
                "os": "Windows 11",
            },
        },
        {
            "name": "HP ZBook Studio G10",
            "price": 62000000,
            "description": "Workstation laptop for professionals, RTX 5000 Ada, color-accurate display",
            "image": "https://images.unsplash.com/photo-1520869e10d9?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900H",
                "ram": "64GB DDR5",
                "storage": "2TB SSD",
                "gpu": "NVIDIA RTX 5000 Ada",
                "screen_size": "16 inch DCI",
                "os": "Windows 11 Pro",
            },
        },
        {
            "name": "Asus ExpertBook B9",
            "price": 41000000,
            "description": "Business ultrabook, certified rugged, excellent security, premium keyboard",
            "image": "https://images.unsplash.com/photo-1515624260622-47375c9646d8?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1365U",
                "ram": "32GB LPDDR5",
                "storage": "1TB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "14 inch OLED",
                "os": "Windows 11 Pro",
            },
        },
        {
            "name": "MSI Prestige 14 Evo",
            "price": 39000000,
            "description": "Creator laptop, Intel Evo platform, excellent build quality, balanced performance",
            "image": "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1365U",
                "ram": "16GB LPDDR5",
                "storage": "512GB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "14 inch 4K OLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "Lenovo Legion Pro 7i",
            "price": 56000000,
            "description": "High-performance gaming, RTX 4080, 16-inch 2.5K display, excellent thermals",
            "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900HX",
                "ram": "32GB DDR5",
                "storage": "1TB SSD",
                "gpu": "NVIDIA RTX 4080",
                "screen_size": "16 inch 2.5K 240Hz",
                "os": "Windows 11",
            },
        },
        {
            "name": "Dell Precision 5470",
            "price": 68000000,
            "description": "Professional CAD/3D workstation, RTX 4500, stunning display, robust security",
            "image": "https://images.unsplash.com/photo-1620825877169-0c6c95f8c39c?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900HK",
                "ram": "64GB DDR5",
                "storage": "2TB SSD",
                "gpu": "NVIDIA RTX 4500 Ada",
                "screen_size": "14 inch 4K OLED",
                "os": "Windows 11 Pro",
            },
        },
        {
            "name": "ASUS Vivobook 15",
            "price": 22000000,
            "description": "Budget-friendly, everyday computing, good battery life, large IPS display",
            "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i5-13420H",
                "ram": "8GB DDR4",
                "storage": "512GB SSD",
                "gpu": "Intel UHD",
                "screen_size": "15.6 inch FHD",
                "os": "Windows 11",
            },
        },
        {
            "name": "HP Pavilion 15",
            "price": 24000000,
            "description": "Affordable mainstream laptop, good multimedia experience, solid build",
            "image": "https://images.unsplash.com/photo-1547448426-86ad64f55dfd?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i5-1235U",
                "ram": "16GB LPDDR5",
                "storage": "512GB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "15.6 inch FHD",
                "os": "Windows 11",
            },
        },
        {
            "name": "Samsung Galaxy Book3 Pro",
            "price": 44000000,
            "description": "Premium Windows ultrabook, AMOLED touchscreen, sleek aluminum design",
            "image": "https://images.unsplash.com/photo-1563291906-7e98c57f3d81?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1360P",
                "ram": "16GB LPDDR5",
                "storage": "512GB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "15.6 inch Dynamic AMOLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "Asus ROG Flow X16",
            "price": 67000000,
            "description": "Gaming convertible 2-in-1, RTX 4090, touchscreen, gaming tablet mode",
            "image": "https://images.unsplash.com/photo-1587829191301-c86b993801ef?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900H",
                "ram": "32GB DDR5",
                "storage": "2TB SSD",
                "gpu": "NVIDIA RTX 4090",
                "screen_size": "16 inch 2.5K OLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "Lenovo ThinkPad P14s Gen5",
            "price": 51000000,
            "description": "Professional ultraportable workstation, RTX 4500, ISV certifications",
            "image": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1365U",
                "ram": "32GB LPDDR5",
                "storage": "1TB SSD",
                "gpu": "NVIDIA RTX 4500 Ada",
                "screen_size": "14 inch 4K OLED",
                "os": "Windows 11 Pro",
            },
        },
        {
            "name": "Acer Predator Triton 16",
            "price": 59000000,
            "description": "Gaming beast, RTX 4080 Super, 16-inch 240Hz display, liquid cooling",
            "image": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900HX",
                "ram": "32GB DDR5",
                "storage": "2TB SSD",
                "gpu": "NVIDIA RTX 4080 Super",
                "screen_size": "16 inch QHD 240Hz",
                "os": "Windows 11",
            },
        },
        {
            "name": "Microsoft Surface Laptop Studio",
            "price": 54000000,
            "description": "Creative professional laptop, dynamic thermal system, RTX 4070, precision touchpad",
            "image": "https://images.unsplash.com/photo-1618519492584-4dd82f3f8f0f?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-13700H",
                "ram": "32GB DDR5",
                "storage": "1TB SSD",
                "gpu": "NVIDIA RTX 4070",
                "screen_size": "15 inch PixelSense",
                "os": "Windows 11",
            },
        },
        {
            "name": "Apple MacBook Pro 14 M3",
            "price": 52000000,
            "description": "Compact powerhouse, M3 Pro chip, Active Cooling, lightweight performer",
            "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Apple M3 Pro",
                "ram": "18GB",
                "storage": "512GB SSD",
                "gpu": "18-core GPU",
                "screen_size": "14 inch Liquid Retina",
                "os": "macOS Sonoma",
            },
        },
        {
            "name": "Zenbook Pro Duo 15",
            "price": 63000000,
            "description": "Dual-screen creativity machine, 4K OLED main + secondary display, RTX 4070",
            "image": "https://images.unsplash.com/photo-1612198188060-c7a0e59819a6?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900H",
                "ram": "32GB LPDDR5",
                "storage": "2TB SSD",
                "gpu": "NVIDIA RTX 4070",
                "screen_size": "15.6 inch + 14 inch OLED",
                "os": "Windows 11",
            },
        },
        {
            "name": "System76 Lemur Pro",
            "price": 36000000,
            "description": "Linux-optimized ultrabook, Intel i7, Pop!_OS, excellent developer experience",
            "image": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i7-1365U",
                "ram": "32GB LPDDR5",
                "storage": "1TB SSD",
                "gpu": "Intel Iris Xe",
                "screen_size": "14 inch 2.8K",
                "os": "Linux Pop!_OS",
            },
        },
        {
            "name": "Gigabyte Aero 15",
            "price": 61000000,
            "description": "Creator laptop, RTX 4070, 4K OLED display, color-accurate performance",
            "image": "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "cpu": "Intel Core i9-13900H",
                "ram": "32GB DDR5",
                "storage": "2TB SSD",
                "gpu": "NVIDIA RTX 4070",
                "screen_size": "15.6 inch 4K OLED",
                "os": "Windows 11",
            },
        },
    ]

    existing = get_existing_names("/api/catalog/products/?type=computer&page_size=200")
    created_or_existing_ids: list[int] = []

    for idx, laptop_data in enumerate(laptops, 1):
        name = laptop_data["name"]
        if name in existing:
            created_or_existing_ids.append(existing[name])
            continue

        payload = {
            "product_type": "computer",
            "name": name,
            "brand": name.split()[0],
            "price": laptop_data["price"],
            "description": laptop_data["description"],
            "image": laptop_data["image"],
            "stock": 3 + (idx % 8),
            "category_id": category_ids[(idx - 1) % len(category_ids)],
            "specs": normalize_specs(laptop_data["specs"], COMPUTER_SPEC_LIMITS),
        }
        status, response = http_json(
            "POST", "/api/catalog/products/", payload, token=token
        )
        if status != 201:
            raise RuntimeError(f"Create laptop '{name}' failed: {status} {response}")
        item_id = response.get("id")
        if isinstance(item_id, int):
            created_or_existing_ids.append(item_id)

    return created_or_existing_ids


def ensure_30_mobiles(token: str, category_ids: list[int]) -> list[int]:
    mobiles = [
        {
            "name": "iPhone 15 Pro Max",
            "price": 38000000,
            "description": "Apple's flagship, A17 Pro chip, 48MP main camera, titanium design, ProMotion display",
            "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.7 inch Super Retina XDR",
                "battery": "4685mAh",
                "camera": "48MP main + 12MP ultra-wide",
                "storage": "256GB",
                "ram": "8GB",
                "os": "iOS 17",
            },
        },
        {
            "name": "iPhone 15 Pro",
            "price": 34000000,
            "description": "Smaller Pro variant, same chip, flat edges, premium materials, excellent camera",
            "image": "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.1 inch Super Retina XDR",
                "battery": "3349mAh",
                "camera": "48MP main + 12MP ultra-wide",
                "storage": "256GB",
                "ram": "8GB",
                "os": "iOS 17",
            },
        },
        {
            "name": "Samsung Galaxy S24 Ultra",
            "price": 36000000,
            "description": "Samsung's ultimate flagship, Snapdragon 8 Gen 3, 200MP camera, titanium frame, 6.8\" display",
            "image": "https://images.unsplash.com/photo-1519070679697-58deaa1cb489?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.8 inch Dynamic AMOLED 2X",
                "battery": "5000mAh",
                "camera": "200MP main + 50MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Samsung Galaxy S24",
            "price": 24000000,
            "description": "Smaller flagship, same latest Snapdragon, 50MP camera, AI-powered features, compact size",
            "image": "https://images.unsplash.com/photo-1572286473122-f66c6a3d8d6e?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.2 inch Dynamic AMOLED 2X",
                "battery": "4000mAh",
                "camera": "50MP main + 12MP ultra-wide",
                "storage": "256GB",
                "ram": "8GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Google Pixel 8 Pro",
            "price": 28000000,
            "description": "Google's phone with Tensor G3, exceptional computational photography, clean Android",
            "image": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.7 inch OLED QHD",
                "battery": "5050mAh",
                "camera": "50MP main + 48MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Google Pixel 8",
            "price": 22000000,
            "description": "Flagship killer, Tensor G3, fantastic camera software, pure Android experience, affordable",
            "image": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.2 inch OLED FHD",
                "battery": "4700mAh",
                "camera": "50MP main + 12MP ultra-wide",
                "storage": "128GB",
                "ram": "8GB",
                "os": "Android 14",
            },
        },
        {
            "name": "OnePlus 12",
            "price": 18000000,
            "description": "Fast performance, Snapdragon 8 Gen 3, 120Hz AMOLED, clean OxygenOS, great value",
            "image": "https://images.unsplash.com/photo-1607936591413-491c52b0e51c?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.7 inch AMOLED FHD",
                "battery": "5400mAh",
                "camera": "50MP main + 48MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Xiaomi 14 Ultra",
            "price": 20000000,
            "description": "Premium flagship, Snapdragon 8 Gen 3, exceptional camera setup, 1.5K resolution screen",
            "image": "https://images.unsplash.com/photo-1511454024649-51d0cade0a5f?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.73 inch AMOLED 1.5K",
                "battery": "5000mAh",
                "camera": "50MP main + 50MP ultra-wide",
                "storage": "512GB",
                "ram": "16GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Xiaomi 14",
            "price": 16000000,
            "description": "Flagship with Leica camera, Snapdragon 8 Gen 3, excellent performance, competitive price",
            "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.36 inch AMOLED FHD",
                "battery": "4610mAh",
                "camera": "50MP main + 50MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "OPPO Find X7",
            "price": 21000000,
            "description": "Premium device, Hasselblad camera, smooth ColorOS, high refresh rate display",
            "image": "https://images.unsplash.com/photo-1556656793-08538906a9f8?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.8 inch AMOLED 4K",
                "battery": "5110mAh",
                "camera": "50MP main + 50MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "vivo X100",
            "price": 19000000,
            "description": "Performance-focused flagship, MediaTek Dimensity, advanced night photography, vibrant AMOLED",
            "image": "https://images.unsplash.com/photo-1549366021-9f761d450615?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.78 inch AMOLED FHD",
                "battery": "5400mAh",
                "camera": "50MP main + 50MP periscope",
                "storage": "512GB",
                "ram": "16GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Motorola Razr 40",
            "price": 26000000,
            "description": "Iconic flip design revived, foldable display, Snapdragon 7 Gen 1, trendy phone",
            "image": "https://images.unsplash.com/photo-1567218065215-2d838d2b6ba0?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.9 inch foldable + 3.6 inch cover",
                "battery": "3800mAh",
                "camera": "50MP main + 13MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 13",
            },
        },
        {
            "name": "Samsung Galaxy Z Flip 5",
            "price": 25000000,
            "description": 'Compact foldable, smaller outer screen, 3.4" inner foldable AMOLED, fashion statement',
            "image": "https://images.unsplash.com/photo-1511391338551-13b3f1f3e0f3?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.7 inch foldable + 3.4 inch cover AMOLED",
                "battery": "3900mAh",
                "camera": "50MP main + 12MP ultra-wide",
                "storage": "256GB",
                "ram": "8GB",
                "os": "Android 13",
            },
        },
        {
            "name": "Nothing Phone 2",
            "price": 15000000,
            "description": "Clear design with LED Glyph interface, Snapdragon 8 Gen 1, unique aesthetic, value flagship",
            "image": "https://images.unsplash.com/photo-1612198188060-c7a0e59819a6?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.7 inch OLED FHD",
                "battery": "4700mAh",
                "camera": "50MP main + 50MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Realme 12 Pro+",
            "price": 12000000,
            "description": "Budget flagship, Snapdragon 7 Gen 3, 50MP camera, large display, incredible value",
            "image": "https://images.unsplash.com/photo-1551960940-a25ab4ccfbf7?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.7 inch AMOLED FHD",
                "battery": "5000mAh",
                "camera": "50MP main + 8MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Poco F5",
            "price": 10000000,
            "description": "Value champion, Snapdragon 7+ Gen 2, 120Hz display, 67W charging, best budget option",
            "image": "https://images.unsplash.com/photo-1511598086775-46a635e96e3d?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.67 inch AMOLED FHD",
                "battery": "5160mAh",
                "camera": "64MP main + 8MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 13",
            },
        },
        {
            "name": "iPhone 14 Pro Max",
            "price": 32000000,
            "description": "Last year's pro flagship, A16 Bionic, Dynamic Island, ProMotion 120Hz, still powerful",
            "image": "https://images.unsplash.com/photo-1511633786486-a01980e01a18?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.7 inch Super Retina XDR",
                "battery": "4323mAh",
                "camera": "48MP main + 12MP ultra-wide",
                "storage": "256GB",
                "ram": "6GB",
                "os": "iOS 17",
            },
        },
        {
            "name": "Samsung Galaxy A54",
            "price": 13000000,
            "description": "Mid-range staple, Exynos 1280, 50MP triple camera, 120Hz AMOLED, practical smartphone",
            "image": "https://images.unsplash.com/photo-1559056199-641a0ac8b3f4?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.4 inch AMOLED FHD",
                "battery": "5000mAh",
                "camera": "50MP main + 12MP ultra-wide",
                "storage": "128GB",
                "ram": "6GB",
                "os": "Android 13",
            },
        },
        {
            "name": "Redmi Note 13 Pro",
            "price": 11000000,
            "description": "Excellent mid-range, Snapdragon 7+ Gen 2, 200MP camera OIS, 120Hz display, great value",
            "image": "https://images.unsplash.com/photo-1514535904405-d3f7e3015f8a?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.67 inch AMOLED FHD",
                "battery": "5000mAh",
                "camera": "200MP main + 8MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 13",
            },
        },
        {
            "name": "Honor Magic 6",
            "price": 23000000,
            "description": "Chinese premium flagship, Snapdragon 8 Gen 3 Leading, advanced AI, premium build quality",
            "image": "https://images.unsplash.com/photo-1545291026-12eb4a249e5d?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.6 inch OLED FHD",
                "battery": "5110mAh",
                "camera": "50MP main + 50MP ultra-wide",
                "storage": "512GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "OnePlus Open",
            "price": 34000000,
            "description": "OnePlus's first foldable, Snapdragon 8 Gen 2 Leading, smooth HyperOS, excellent foldable",
            "image": "https://images.unsplash.com/photo-1618519492584-4dd82f3f8f0f?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "7.82 inch foldable + 6.31 inch cover AMOLED",
                "battery": "4805mAh",
                "camera": "48MP main + 50MP ultra-wide",
                "storage": "512GB",
                "ram": "16GB",
                "os": "Android 13",
            },
        },
        {
            "name": "Samsung Galaxy Z Fold 5",
            "price": 35000000,
            "description": 'Premium foldable tablet phone, 7.6" inner display, Snapdragon 8 Gen 2, ultimate multitasker',
            "image": "https://images.unsplash.com/photo-1556656793-08538906a9f8?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "7.6 inch foldable + 6.2 inch cover AMOLED",
                "battery": "4400mAh",
                "camera": "50MP main + 50MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 13",
            },
        },
        {
            "name": "Apple iPhone 15",
            "price": 28000000,
            "description": "Standard iPhone 15, A17 Pro, USB-C, Dynamic Island on all models, great daily driver",
            "image": "https://images.unsplash.com/photo-1517457373614-b7152f800fd1?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.1 inch Super Retina XDR",
                "battery": "3349mAh",
                "camera": "48MP main + 12MP ultra-wide",
                "storage": "128GB",
                "ram": "6GB",
                "os": "iOS 17",
            },
        },
        {
            "name": "Huawei Mate 60 Pro",
            "price": 30000000,
            "description": "Chinese flagship without Google, HarmonyOS, 48MP Leica camera, premium build and design",
            "image": "https://images.unsplash.com/photo-1607953527521-59489378b41b?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.82 inch OLED FHD",
                "battery": "5110mAh",
                "camera": "48MP main + 40MP ultra-wide",
                "storage": "512GB",
                "ram": "12GB",
                "os": "HarmonyOS 4.0",
            },
        },
        {
            "name": "TCL 50 Ultra",
            "price": 14000000,
            "description": "Budget ultra with big screen, Snapdragon 695, large battery, good multimedia phone",
            "image": "https://images.unsplash.com/photo-1521297944000-6d4f3a0004a3?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.8 inch IPS FHD",
                "battery": "5010mAh",
                "camera": "50MP main + 8MP ultra-wide",
                "storage": "256GB",
                "ram": "8GB",
                "os": "Android 13",
            },
        },
        {
            "name": "Motorola Edge 50",
            "price": 17000000,
            "description": "Mid-range near-stock Android, Snapdragon 7 Gen 3, clean experience, practical features",
            "image": "https://images.unsplash.com/photo-1516321318423-f06f70db51ba?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.4 inch AMOLED FHD",
                "battery": "4500mAh",
                "camera": "50MP main + 13MP ultra-wide",
                "storage": "256GB",
                "ram": "12GB",
                "os": "Android 14",
            },
        },
        {
            "name": "Samsung Galaxy A15",
            "price": 8000000,
            "description": "Budget Android, MediaTek Dimensity, 50MP main camera, 90Hz display, great starter phone",
            "image": "https://images.unsplash.com/photo-1514437267127-f1241c1ee0f2?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.5 inch IPS FHD",
                "battery": "5000mAh",
                "camera": "50MP main + 5MP ultra-wide",
                "storage": "128GB",
                "ram": "4GB",
                "os": "Android 14",
            },
        },
        {
            "name": "iPhone 13",
            "price": 20000000,
            "description": "Previous gen iPhone, A15 Bionic, still excellent performance, good discount from 15",
            "image": "https://images.unsplash.com/photo-1592286927505-1fed6a12e923?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "screen_size": "6.1 inch Super Retina XDR",
                "battery": "3240mAh",
                "camera": "12MP main + 12MP ultra-wide",
                "storage": "128GB",
                "ram": "4GB",
                "os": "iOS 17",
            },
        },
    ]

    existing = get_existing_names("/api/catalog/products/?type=mobile&page_size=200")
    created_or_existing_ids: list[int] = []

    for idx, mobile_data in enumerate(mobiles, 1):
        name = mobile_data["name"]
        if name in existing:
            created_or_existing_ids.append(existing[name])
            continue

        payload = {
            "product_type": "mobile",
            "name": name,
            "brand": name.split()[0],
            "price": mobile_data["price"],
            "description": mobile_data["description"],
            "image": mobile_data["image"],
            "stock": 5 + (idx % 12),
            "category_id": category_ids[(idx - 1) % len(category_ids)],
            "specs": normalize_specs(mobile_data["specs"], MOBILE_SPEC_LIMITS),
        }
        status, response = http_json(
            "POST", "/api/catalog/products/", payload, token=token
        )
        if status != 201:
            raise RuntimeError(f"Create mobile '{name}' failed: {status} {response}")
        item_id = response.get("id")
        if isinstance(item_id, int):
            created_or_existing_ids.append(item_id)

    return created_or_existing_ids


CLOTHES_SPEC_LIMITS = {
    "size": 5,
    "color": 50,
    "material": 100,
}


def ensure_50_clothes(token: str, category_ids: list[int]) -> list[int]:
    clothes_items = [
        {
            "name": "Áo thun Basic Premium",
            "brand": "H&M",
            "price": 199000,
            "gender": "unisex",
            "description": "Áo thun cotton 100% thoáng mát, phù hợp mặc hàng ngày",
            "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Trắng", "material": "Cotton 100%"},
        },
        {
            "name": "Áo sơ mi Oxford Classic",
            "brand": "Uniqlo",
            "price": 590000,
            "gender": "male",
            "description": "Áo sơ mi Oxford phong cách công sở, chất liệu bền đẹp",
            "image": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Xanh nhạt", "material": "Cotton Oxford"},
        },
        {
            "name": "Quần jean Slim Fit",
            "brand": "Levi's",
            "price": 1290000,
            "gender": "male",
            "description": "Quần jean slim fit co giãn, form đẹp, thoải mái vận động",
            "image": "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Xanh đậm", "material": "Denim stretch"},
        },
        {
            "name": "Váy liền hoa nhí",
            "brand": "Zara",
            "price": 890000,
            "gender": "female",
            "description": "Váy liền họa tiết hoa nhí, phong cách vintage nữ tính",
            "image": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Hồng", "material": "Voan"},
        },
        {
            "name": "Áo khoác Bomber",
            "brand": "Nike",
            "price": 1890000,
            "gender": "unisex",
            "description": "Áo khoác bomber thể thao, chống gió nhẹ, phong cách street",
            "image": "https://images.unsplash.com/photo-1551028719-00167b16eac5?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "XL", "color": "Đen", "material": "Polyester"},
        },
        {
            "name": "Quần short kaki",
            "brand": "GAP",
            "price": 490000,
            "gender": "male",
            "description": "Quần short kaki thoáng mát, phù hợp mùa hè",
            "image": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Be", "material": "Kaki cotton"},
        },
        {
            "name": "Áo thun Polo Classic",
            "brand": "Lacoste",
            "price": 2490000,
            "gender": "male",
            "description": "Áo polo cổ điển, chất liệu pique cotton cao cấp",
            "image": "https://images.unsplash.com/photo-1586363104862-3a5e2ab60d99?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Xanh navy", "material": "Pique cotton"},
        },
        {
            "name": "Đầm maxi dạ hội",
            "brand": "Mango",
            "price": 1590000,
            "gender": "female",
            "description": "Đầm maxi thanh lịch, phù hợp sự kiện và dạ tiệc",
            "image": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Đỏ", "material": "Lụa satin"},
        },
        {
            "name": "Áo hoodie Oversize",
            "brand": "Adidas",
            "price": 1290000,
            "gender": "unisex",
            "description": "Áo hoodie oversize ấm áp, phong cách streetwear",
            "image": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "XL", "color": "Xám", "material": "Cotton fleece"},
        },
        {
            "name": "Quần jean Mom Fit",
            "brand": "Zara",
            "price": 990000,
            "gender": "female",
            "description": "Quần jean mom fit cạp cao, phong cách retro trẻ trung",
            "image": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Xanh nhạt", "material": "Denim"},
        },
        {
            "name": "Áo thun graphic Anime",
            "brand": "Uniqlo",
            "price": 390000,
            "gender": "unisex",
            "description": "Áo thun in hình anime, chất cotton mềm mại",
            "image": "https://images.unsplash.com/photo-1503341504253-dff4815485f1?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Đen", "material": "Cotton"},
        },
        {
            "name": "Áo sơ mi linen",
            "brand": "MUJI",
            "price": 790000,
            "gender": "male",
            "description": "Áo sơ mi linen tự nhiên, thoáng mát cho mùa hè",
            "image": "https://images.unsplash.com/photo-1598033129183-c4f50c736c10?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Trắng", "material": "Linen"},
        },
        {
            "name": "Váy midi xếp ly",
            "brand": "H&M",
            "price": 690000,
            "gender": "female",
            "description": "Váy midi xếp ly thanh lịch, phù hợp đi làm và đi chơi",
            "image": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Đen", "material": "Polyester blend"},
        },
        {
            "name": "Áo khoác denim Trucker",
            "brand": "Levi's",
            "price": 2190000,
            "gender": "unisex",
            "description": "Áo khoác denim cổ điển, phong cách bụi bặm",
            "image": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Xanh medium", "material": "Denim"},
        },
        {
            "name": "Quần short thể thao",
            "brand": "Nike",
            "price": 590000,
            "gender": "male",
            "description": "Quần short thể thao Dri-FIT, khô nhanh, thoải mái tập gym",
            "image": "https://images.unsplash.com/photo-1562157873-818bc0726f68?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Đen", "material": "Polyester Dri-FIT"},
        },
        {
            "name": "Áo thun crop top",
            "brand": "Zara",
            "price": 350000,
            "gender": "female",
            "description": "Áo thun crop top trẻ trung, phối đồ linh hoạt",
            "image": "https://images.unsplash.com/photo-1594938298603-c8148c4dae35?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Trắng", "material": "Cotton spandex"},
        },
        {
            "name": "Áo Polo Sport",
            "brand": "Adidas",
            "price": 890000,
            "gender": "male",
            "description": "Áo polo thể thao, chất liệu thoáng khí, co giãn tốt",
            "image": "https://images.unsplash.com/photo-1625910513413-5fc421e0b6cd?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Trắng", "material": "Polyester mesh"},
        },
        {
            "name": "Quần jean skinny đen",
            "brand": "Topman",
            "price": 790000,
            "gender": "male",
            "description": "Quần jean skinny đen basic, phối được nhiều kiểu",
            "image": "https://images.unsplash.com/photo-1475178626620-a4d074967452?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Đen", "material": "Denim stretch"},
        },
        {
            "name": "Đầm sơ mi công sở",
            "brand": "Mango",
            "price": 1190000,
            "gender": "female",
            "description": "Đầm sơ mi thanh lịch phong cách công sở hiện đại",
            "image": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Xanh navy", "material": "Cotton poplin"},
        },
        {
            "name": "Áo khoác puffer nhẹ",
            "brand": "Uniqlo",
            "price": 1490000,
            "gender": "unisex",
            "description": "Áo khoác phao siêu nhẹ, giữ ấm tốt, gấp gọn dễ dàng",
            "image": "https://images.unsplash.com/photo-1544923246-77307dd270aa?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Đen", "material": "Nylon lông vũ"},
        },
        {
            "name": "Áo thun V-neck",
            "brand": "GAP",
            "price": 290000,
            "gender": "male",
            "description": "Áo thun cổ V thoải mái, chất cotton mềm mại",
            "image": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Xám đậm", "material": "Cotton"},
        },
        {
            "name": "Quần short linen",
            "brand": "MUJI",
            "price": 590000,
            "gender": "male",
            "description": "Quần short linen thoáng mát, phù hợp đi biển và nghỉ dưỡng",
            "image": "https://images.unsplash.com/photo-1565084888279-aca607ecce0c?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Be", "material": "Linen"},
        },
        {
            "name": "Áo sơ mi kẻ caro",
            "brand": "Burberry",
            "price": 3590000,
            "gender": "male",
            "description": "Áo sơ mi kẻ caro cao cấp, phong cách British classic",
            "image": "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "size": "M",
                "color": "Kẻ caro nâu",
                "material": "Cotton cao cấp",
            },
        },
        {
            "name": "Váy tennis xếp ly",
            "brand": "Nike",
            "price": 890000,
            "gender": "female",
            "description": "Váy tennis phong cách sporty chic, có quần lót bên trong",
            "image": "https://images.unsplash.com/photo-1582142306909-195b907cdfa4?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Trắng", "material": "Polyester"},
        },
        {
            "name": "Áo khoác blazer nam",
            "brand": "Zara",
            "price": 1890000,
            "gender": "male",
            "description": "Áo blazer form slim, phù hợp đi làm lẫn dạo phố",
            "image": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Đen", "material": "Polyester wool blend"},
        },
        {
            "name": "Áo thun raglan",
            "brand": "Champion",
            "price": 490000,
            "gender": "unisex",
            "description": "Áo thun raglan phối màu, phong cách thể thao retro",
            "image": "https://images.unsplash.com/photo-1529374255404-311a2a4f1fd9?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Trắng/Đỏ", "material": "Cotton jersey"},
        },
        {
            "name": "Quần jean wide leg",
            "brand": "H&M",
            "price": 690000,
            "gender": "female",
            "description": "Quần jean ống rộng, phong cách thập niên 90, cạp cao",
            "image": "https://images.unsplash.com/photo-1551854838-212c50b4c184?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Xanh nhạt", "material": "Denim"},
        },
        {
            "name": "Áo cardigan len",
            "brand": "Uniqlo",
            "price": 790000,
            "gender": "female",
            "description": "Áo cardigan len mềm mại, ấm áp cho mùa thu đông",
            "image": "https://images.unsplash.com/photo-1434389677669-e08b4cda3f30?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Kem", "material": "Len merino"},
        },
        {
            "name": "Quần short jogger",
            "brand": "Adidas",
            "price": 690000,
            "gender": "unisex",
            "description": "Quần short jogger thể thao, lưng thun thoải mái",
            "image": "https://images.unsplash.com/photo-1560243563-062bfc001d68?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Xám", "material": "French terry"},
        },
        {
            "name": "Áo thun oversize streetwear",
            "brand": "Stussy",
            "price": 890000,
            "gender": "unisex",
            "description": "Áo thun oversize phong cách đường phố, in logo nổi bật",
            "image": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "XL", "color": "Đen", "material": "Cotton heavyweight"},
        },
        {
            "name": "Áo sơ mi trắng dài tay",
            "brand": "Ralph Lauren",
            "price": 2790000,
            "gender": "male",
            "description": "Áo sơ mi trắng classic fit, chất lượng cao cấp",
            "image": "https://images.unsplash.com/photo-1620012253295-c15cc3e65df4?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Trắng", "material": "Cotton poplin"},
        },
        {
            "name": "Váy wrap chấm bi",
            "brand": "Reformation",
            "price": 1390000,
            "gender": "female",
            "description": "Váy wrap chấm bi nữ tính, thiết kế tôn dáng",
            "image": "https://images.unsplash.com/photo-1585487000160-6ebcfceb0d44?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Đen/Trắng", "material": "Viscose"},
        },
        {
            "name": "Áo khoác gió chạy bộ",
            "brand": "Nike",
            "price": 1690000,
            "gender": "unisex",
            "description": "Áo khoác gió siêu nhẹ, chống nước, phản quang an toàn",
            "image": "https://images.unsplash.com/photo-1495105787522-5334e3ffa0ef?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Đen", "material": "Ripstop nylon"},
        },
        {
            "name": "Quần jogger thun dài",
            "brand": "Champion",
            "price": 790000,
            "gender": "unisex",
            "description": "Quần jogger thun co giãn, mặc nhà hoặc đi dạo đều phù hợp",
            "image": "https://images.unsplash.com/photo-1552902865-b72c031ac5ea?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Xám", "material": "Cotton fleece"},
        },
        {
            "name": "Áo thun tank top gym",
            "brand": "Under Armour",
            "price": 490000,
            "gender": "male",
            "description": "Tank top tập gym, thoáng khí, khô nhanh",
            "image": "https://images.unsplash.com/photo-1534368786749-b63e05c92717?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Đen", "material": "Polyester HeatGear"},
        },
        {
            "name": "Đầm babydoll",
            "brand": "Forever 21",
            "price": 450000,
            "gender": "female",
            "description": "Đầm babydoll trẻ trung, cổ vuông, tay phồng nhẹ",
            "image": "https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Vàng pastel", "material": "Cotton lawn"},
        },
        {
            "name": "Quần tây âu slim",
            "brand": "Zara",
            "price": 990000,
            "gender": "male",
            "description": "Quần tây âu form slim, lịch lãm cho dân công sở",
            "image": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Đen", "material": "Polyester viscose"},
        },
        {
            "name": "Áo croptop thể thao",
            "brand": "Adidas",
            "price": 590000,
            "gender": "female",
            "description": "Áo croptop thể thao, hỗ trợ tốt khi tập luyện",
            "image": "https://images.unsplash.com/photo-1571945153237-4929e783af4a?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Hồng", "material": "Nylon spandex"},
        },
        {
            "name": "Áo khoác varsity",
            "brand": "GAP",
            "price": 1990000,
            "gender": "unisex",
            "description": "Áo khoác varsity phong cách retro Mỹ, phối logo thêu",
            "image": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&w=1200&q=80",
            "specs": {
                "size": "L",
                "color": "Xanh navy/Trắng",
                "material": "Wool blend",
            },
        },
        {
            "name": "Áo thun Henley trơn",
            "brand": "H&M",
            "price": 250000,
            "gender": "male",
            "description": "Áo thun Henley cổ nút, phong cách casual nam tính",
            "image": "https://images.unsplash.com/photo-1622470953794-aa9c70b0fb9d?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Xám nhạt", "material": "Cotton"},
        },
        {
            "name": "Quần culottes nữ",
            "brand": "Mango",
            "price": 790000,
            "gender": "female",
            "description": "Quần culottes ống rộng, thanh lịch cho mùa hè",
            "image": "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Đen", "material": "Viscose"},
        },
        {
            "name": "Áo sơ mi flannel",
            "brand": "Uniqlo",
            "price": 690000,
            "gender": "unisex",
            "description": "Áo sơ mi flannel ấm áp, kẻ caro phong cách lumberjack",
            "image": "https://images.unsplash.com/photo-1523381294911-8d3cead13475?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Đỏ kẻ", "material": "Cotton flannel"},
        },
        {
            "name": "Váy Jean chữ A",
            "brand": "Levi's",
            "price": 890000,
            "gender": "female",
            "description": "Váy jean chữ A cổ điển, phối được nhiều kiểu áo",
            "image": "https://images.unsplash.com/photo-1583846783214-7229fcb4e0e0?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Xanh medium", "material": "Denim"},
        },
        {
            "name": "Áo khoác trench coat",
            "brand": "Burberry",
            "price": 4990000,
            "gender": "female",
            "description": "Áo trench coat kinh điển, chống nước, sang trọng",
            "image": "https://images.unsplash.com/photo-1544022613-e87ca75a784a?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Be", "material": "Cotton gabardine"},
        },
        {
            "name": "Áo thun dài tay basic",
            "brand": "MUJI",
            "price": 390000,
            "gender": "unisex",
            "description": "Áo thun dài tay basic, chất liệu organic cotton",
            "image": "https://images.unsplash.com/photo-1611601322175-ef85023317a8?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Trắng", "material": "Organic cotton"},
        },
        {
            "name": "Quần legging tập yoga",
            "brand": "Lululemon",
            "price": 1890000,
            "gender": "female",
            "description": "Quần legging cao cấp, cạp cao, co giãn 4 chiều",
            "image": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "S", "color": "Đen", "material": "Nulu fabric"},
        },
        {
            "name": "Áo Polo Ralph Lauren",
            "brand": "Ralph Lauren",
            "price": 2890000,
            "gender": "male",
            "description": "Áo polo biểu tượng với logo thêu, chất liệu mesh cotton",
            "image": "https://images.unsplash.com/photo-1571455786673-9d9d6c194f90?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Xanh navy", "material": "Cotton mesh"},
        },
        {
            "name": "Quần jean Boyfriend",
            "brand": "GAP",
            "price": 890000,
            "gender": "female",
            "description": "Quần jean boyfriend rộng thoải mái, wash vintage",
            "image": "https://images.unsplash.com/photo-1604176354204-9268737828e4?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "M", "color": "Xanh wash", "material": "Denim"},
        },
        {
            "name": "Áo hoodie zip qua đầu",
            "brand": "Champion",
            "price": 1190000,
            "gender": "unisex",
            "description": "Áo hoodie có khóa kéo, logo thêu ngực, ấm áp mùa đông",
            "image": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "XL", "color": "Xám đậm", "material": "Cotton fleece"},
        },
        {
            "name": "Áo sơ mi Cuban Resort",
            "brand": "Mango",
            "price": 990000,
            "gender": "male",
            "description": "Áo sơ mi cổ Cuban thoáng mát, phù hợp du lịch và mùa hè",
            "image": "https://images.unsplash.com/photo-1602810316693-3667c854239a?auto=format&fit=crop&w=1200&q=80",
            "specs": {"size": "L", "color": "Kem", "material": "Rayon blend"},
        },
    ]

    existing = get_existing_names("/api/catalog/products/?type=clothes&page_size=200")
    created_or_existing_ids: list[int] = []

    for idx, clothes_data in enumerate(clothes_items, 1):
        name = clothes_data["name"]
        if name in existing:
            created_or_existing_ids.append(existing[name])
            continue

        payload = {
            "product_type": "clothes",
            "name": name,
            "brand": clothes_data["brand"],
            "price": clothes_data["price"],
            "description": clothes_data["description"],
            "image": clothes_data["image"],
            "stock": 5 + (idx % 15),
            "gender": clothes_data["gender"],
            "category_id": category_ids[(idx - 1) % len(category_ids)],
            "specs": normalize_specs(clothes_data["specs"], CLOTHES_SPEC_LIMITS),
        }
        status, response = http_json(
            "POST", "/api/catalog/products/", payload, token=token
        )
        if status != 201:
            raise RuntimeError(f"Create clothes '{name}' failed: {status} {response}")
        item_id = response.get("id")
        if isinstance(item_id, int):
            created_or_existing_ids.append(item_id)

    return created_or_existing_ids


EXTENDED_CATALOG = {
    "tablet": {
        "resource": "tablets",
        "categories": [
            ("Tablet cao cấp", "Hiệu năng cao, màn hình đẹp"),
            ("Tablet học tập", "Gọn nhẹ cho học sinh sinh viên"),
            ("Tablet doanh nghiệp", "Bảo mật và phụ kiện bút bàn phím"),
        ],
        "products": [
            {
                "name": "iPad Pro 13 M4 Wi-Fi 256GB",
                "brand": "Apple",
                "price": 34990000,
                "description": "Tablet cao cấp với chip Apple M4, màn hình Ultra Retina XDR và hỗ trợ Apple Pencil Pro.",
                "image": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Apple M4",
                    "ram": "8GB",
                    "storage": "256GB",
                    "gpu": "Apple GPU",
                    "screen_size": "13 inch OLED",
                    "os": "iPadOS 18",
                },
            },
            {
                "name": "Samsung Galaxy Tab S9 Ultra 256GB",
                "brand": "Samsung",
                "price": 26990000,
                "description": "Tablet Android màn hình lớn 14.6 inch, bút S Pen đi kèm, phù hợp giải trí và sáng tạo.",
                "image": "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Snapdragon 8 Gen 2",
                    "ram": "12GB",
                    "storage": "256GB",
                    "gpu": "Adreno",
                    "screen_size": "14.6 inch AMOLED",
                    "os": "Android 14",
                },
            },
            {
                "name": "Xiaomi Pad 6S Pro 12.4",
                "brand": "Xiaomi",
                "price": 15990000,
                "description": "Tablet tầm trung cao với màn hình 144Hz và pin lớn, phù hợp học tập và làm việc.",
                "image": "https://images.unsplash.com/photo-1561154464-82e9adf32764?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Snapdragon 8 Gen 2",
                    "ram": "8GB",
                    "storage": "256GB",
                    "gpu": "Adreno",
                    "screen_size": "12.4 inch LCD",
                    "os": "Android 14",
                },
            },
            {
                "name": "Lenovo Tab P12 Matte Display",
                "brand": "Lenovo",
                "price": 11990000,
                "description": "Tablet 12.7 inch anti-glare, trải nghiệm đọc và ghi chú tốt, pin bền.",
                "image": "https://images.unsplash.com/photo-1611078489935-0cb964de46d6?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Dimensity 7050",
                    "ram": "8GB",
                    "storage": "128GB",
                    "gpu": "Mali",
                    "screen_size": "12.7 inch 3K",
                    "os": "Android 14",
                },
            },
            {
                "name": "Huawei MatePad 11.5 PaperMatte",
                "brand": "Huawei",
                "price": 9990000,
                "description": "Tablet màn nhám chống chói, tối ưu ghi chú và học trực tuyến.",
                "image": "https://images.unsplash.com/photo-1510552776732-03e61cf4b144?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Kirin 9000",
                    "ram": "8GB",
                    "storage": "128GB",
                    "gpu": "Mali",
                    "screen_size": "11.5 inch",
                    "os": "HarmonyOS",
                },
            },
            {
                "name": "iPad Air 11 M2 Wi-Fi 128GB",
                "brand": "Apple",
                "price": 18990000,
                "description": "Thiết kế nhẹ, hiệu năng mạnh, phù hợp cả học tập và làm việc hằng ngày.",
                "image": "https://images.unsplash.com/photo-1589739900243-4b52cd9dd8df?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Apple M2",
                    "ram": "8GB",
                    "storage": "128GB",
                    "gpu": "Apple GPU",
                    "screen_size": "11 inch",
                    "os": "iPadOS 18",
                },
            },
        ],
    },
    "audio": {
        "resource": "audios",
        "categories": [
            ("Tai nghe không dây", "Tai nghe ANC và TWS"),
            ("Loa bluetooth", "Loa di động và loa bàn"),
            ("Thiết bị thu âm", "Micro và phụ kiện livestream"),
        ],
        "products": [
            {
                "name": "Sony WH-1000XM5",
                "brand": "Sony",
                "price": 7990000,
                "description": "Tai nghe chống ồn cao cấp với chất âm cân bằng và thời lượng pin dài.",
                "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "QN1",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Over-ear",
                    "os": "Bluetooth 5.3",
                },
            },
            {
                "name": "Apple AirPods Pro 2 USB-C",
                "brand": "Apple",
                "price": 5790000,
                "description": "TWS cao cấp, ANC tốt, tương thích sâu với hệ sinh thái Apple.",
                "image": "https://images.unsplash.com/photo-1606220838315-056192d5e927?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "H2",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "In-ear",
                    "os": "Bluetooth 5.3",
                },
            },
            {
                "name": "JBL Charge 5",
                "brand": "JBL",
                "price": 3590000,
                "description": "Loa bluetooth chống nước, pin trâu, phù hợp dã ngoại và tiệc nhỏ.",
                "image": "https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "DSP",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Loa 40W",
                    "os": "Bluetooth 5.1",
                },
            },
            {
                "name": "Marshall Stanmore III",
                "brand": "Marshall",
                "price": 8990000,
                "description": "Loa để bàn phong cách vintage, chất âm mạnh và chi tiết.",
                "image": "https://images.unsplash.com/photo-1589003077984-894e133dabab?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "DSP",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Loa 80W",
                    "os": "Bluetooth 5.2",
                },
            },
            {
                "name": "Audio-Technica AT2020USB-X",
                "brand": "Audio-Technica",
                "price": 4990000,
                "description": "Micro thu âm USB chất lượng cao cho podcast và streaming.",
                "image": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "24-bit ADC",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Micro condenser",
                    "os": "USB-C",
                },
            },
            {
                "name": "Sennheiser Momentum 4 Wireless",
                "brand": "Sennheiser",
                "price": 6990000,
                "description": "Tai nghe bluetooth pin tới 60 giờ, phù hợp nghe nhạc chất lượng cao.",
                "image": "https://images.unsplash.com/photo-1484704849700-f032a568e944?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "DSP",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Over-ear",
                    "os": "Bluetooth 5.2",
                },
            },
        ],
    },
    "wearable": {
        "resource": "wearables",
        "categories": [
            ("Smartwatch", "Đồng hồ thông minh theo dõi sức khỏe"),
            ("Vòng đeo tay", "Thiết bị theo dõi vận động"),
            ("Thiết bị thể thao", "Wearable chuyên dụng luyện tập"),
        ],
        "products": [
            {
                "name": "Apple Watch Series 9 GPS 45mm",
                "brand": "Apple",
                "price": 10990000,
                "description": "Đồng hồ thông minh cao cấp, theo dõi sức khỏe và tập luyện toàn diện.",
                "image": "https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "S9 SiP",
                    "ram": "1GB",
                    "storage": "64GB",
                    "gpu": "N/A",
                    "screen_size": "45mm OLED",
                    "os": "watchOS",
                },
            },
            {
                "name": "Samsung Galaxy Watch6 Classic 47mm",
                "brand": "Samsung",
                "price": 7990000,
                "description": "Thiết kế vòng xoay cổ điển, hỗ trợ theo dõi nhịp tim và giấc ngủ chính xác.",
                "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Exynos W930",
                    "ram": "2GB",
                    "storage": "16GB",
                    "gpu": "N/A",
                    "screen_size": "47mm AMOLED",
                    "os": "Wear OS",
                },
            },
            {
                "name": "Garmin Forerunner 265",
                "brand": "Garmin",
                "price": 9990000,
                "description": "Smartwatch thể thao chuyên chạy bộ với GPS đa băng tần.",
                "image": "https://images.unsplash.com/photo-1579586337278-3f436f25d4d6?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Garmin SoC",
                    "ram": "N/A",
                    "storage": "8GB",
                    "gpu": "N/A",
                    "screen_size": "1.3 inch",
                    "os": "Garmin OS",
                },
            },
            {
                "name": "Huawei Watch GT 4",
                "brand": "Huawei",
                "price": 5490000,
                "description": "Thiết kế thời trang, pin tốt, theo dõi luyện tập đa môn.",
                "image": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "ARM Cortex",
                    "ram": "N/A",
                    "storage": "4GB",
                    "gpu": "N/A",
                    "screen_size": "1.43 inch AMOLED",
                    "os": "HarmonyOS",
                },
            },
            {
                "name": "Xiaomi Smart Band 8 Pro",
                "brand": "Xiaomi",
                "price": 1690000,
                "description": "Vòng đeo tay thông minh với màn hình lớn và theo dõi sức khỏe 24/7.",
                "image": "https://images.unsplash.com/photo-1617043786394-f977fa12eddf?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Low-power MCU",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "1.74 inch AMOLED",
                    "os": "Xiaomi OS",
                },
            },
            {
                "name": "Fitbit Charge 6",
                "brand": "Fitbit",
                "price": 4290000,
                "description": "Thiết bị theo dõi tập luyện, nhịp tim và stress với độ chính xác cao.",
                "image": "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Fitbit SoC",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "AMOLED",
                    "os": "Fitbit OS",
                },
            },
        ],
    },
    "component": {
        "resource": "components",
        "categories": [
            ("CPU", "Bộ vi xử lý desktop và workstation"),
            ("GPU", "Card đồ họa gaming và dựng phim"),
            ("RAM & SSD", "Nâng cấp bộ nhớ và lưu trữ"),
        ],
        "products": [
            {
                "name": "Intel Core i7-14700K",
                "brand": "Intel",
                "price": 10990000,
                "description": "CPU desktop hiệu năng cao cho gaming và làm việc đa nhiệm.",
                "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "20 cores",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "Intel UHD",
                    "screen_size": "LGA1700",
                    "os": "Windows/Linux",
                },
            },
            {
                "name": "AMD Ryzen 9 7950X3D",
                "brand": "AMD",
                "price": 16990000,
                "description": "CPU cao cấp cho game thủ và creator với bộ nhớ cache 3D.",
                "image": "https://images.unsplash.com/photo-1591799265444-d66432b91588?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "16 cores",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "Radeon iGPU",
                    "screen_size": "AM5",
                    "os": "Windows/Linux",
                },
            },
            {
                "name": "NVIDIA GeForce RTX 4070 Super",
                "brand": "NVIDIA",
                "price": 20990000,
                "description": "GPU mạnh cho chơi game 2K và xử lý AI cơ bản.",
                "image": "https://images.unsplash.com/photo-1591488320449-011701bb6704?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "12GB GDDR6X",
                    "storage": "N/A",
                    "gpu": "RTX 4070 Super",
                    "screen_size": "PCIe 4.0",
                    "os": "Windows/Linux",
                },
            },
            {
                "name": "MSI GeForce RTX 4060 Ti 16GB",
                "brand": "MSI",
                "price": 14990000,
                "description": "Card đồ họa tầm trung cao, phù hợp gaming và đồ họa 1080p/1440p.",
                "image": "https://images.unsplash.com/photo-1587202372775-e229f1724f10?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "16GB GDDR6",
                    "storage": "N/A",
                    "gpu": "RTX 4060 Ti",
                    "screen_size": "PCIe 4.0",
                    "os": "Windows/Linux",
                },
            },
            {
                "name": "Corsair Vengeance DDR5 32GB 6000",
                "brand": "Corsair",
                "price": 3490000,
                "description": "RAM DDR5 32GB bus cao, tối ưu cho hệ thống hiệu năng.",
                "image": "https://images.unsplash.com/photo-1562976540-1502c2145186?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "32GB DDR5",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "DIMM",
                    "os": "Windows/Linux",
                },
            },
            {
                "name": "Samsung 990 PRO 2TB NVMe",
                "brand": "Samsung",
                "price": 4590000,
                "description": "SSD NVMe tốc độ cao cho hệ thống gaming và workstation.",
                "image": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "2TB NVMe",
                    "gpu": "N/A",
                    "screen_size": "M.2 2280",
                    "os": "Windows/Linux",
                },
            },
        ],
    },
    "peripheral": {
        "resource": "peripherals",
        "categories": [
            ("Chuột", "Chuột gaming và văn phòng"),
            ("Bàn phím", "Bàn phím cơ và không dây"),
            ("Webcam", "Thiết bị họp online và stream"),
        ],
        "products": [
            {
                "name": "Logitech MX Master 3S",
                "brand": "Logitech",
                "price": 2590000,
                "description": "Chuột không dây cao cấp cho dân văn phòng và sáng tạo.",
                "image": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "8000 DPI",
                    "os": "Windows/macOS",
                },
            },
            {
                "name": "Razer DeathAdder V3 Pro",
                "brand": "Razer",
                "price": 2990000,
                "description": "Chuột gaming siêu nhẹ, cảm biến chính xác cho eSports.",
                "image": "https://images.unsplash.com/photo-1613141412501-9012977f1969?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "30000 DPI",
                    "os": "Windows",
                },
            },
            {
                "name": "Keychron K8 Pro",
                "brand": "Keychron",
                "price": 2690000,
                "description": "Bàn phím cơ không dây hỗ trợ Mac/Windows, hot-swap switch.",
                "image": "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Tenkeyless",
                    "os": "Windows/macOS",
                },
            },
            {
                "name": "Logitech G Pro X TKL",
                "brand": "Logitech",
                "price": 3490000,
                "description": "Bàn phím gaming TKL độ trễ thấp, tối ưu thi đấu.",
                "image": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Tenkeyless",
                    "os": "Windows",
                },
            },
            {
                "name": "Elgato Facecam MK.2",
                "brand": "Elgato",
                "price": 4290000,
                "description": "Webcam Full HD cho livestream và họp trực tuyến chuyên nghiệp.",
                "image": "https://images.unsplash.com/photo-1587826080692-f439cd0b70da?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "1080p60",
                    "os": "Windows/macOS",
                },
            },
            {
                "name": "Anker PowerConf C302",
                "brand": "Anker",
                "price": 2090000,
                "description": "Webcam góc rộng, hình ảnh nét cho nhu cầu làm việc hybrid.",
                "image": "https://images.unsplash.com/photo-1623949556303-b0d17d198863?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "2K",
                    "os": "Windows/macOS",
                },
            },
        ],
    },
    "monitor": {
        "resource": "monitors",
        "categories": [
            ("Màn hình gaming", "Tần số quét cao cho game"),
            ("Màn hình đồ họa", "Chuẩn màu cho thiết kế"),
            ("Màn hình văn phòng", "Tối ưu làm việc hằng ngày"),
        ],
        "products": [
            {
                "name": "LG UltraGear 27GP850-B",
                "brand": "LG",
                "price": 8990000,
                "description": "Màn hình gaming 27 inch QHD 165Hz, phản hồi nhanh.",
                "image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "G-Sync Compatible",
                    "screen_size": "27 inch QHD 165Hz",
                    "os": "Windows/macOS",
                },
            },
            {
                "name": "Samsung Odyssey G7 32",
                "brand": "Samsung",
                "price": 13990000,
                "description": "Màn hình cong 32 inch QHD 240Hz cho game thủ chuyên nghiệp.",
                "image": "https://images.unsplash.com/photo-1529336953121-ad5a0d43d0d2?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "FreeSync Premium",
                    "screen_size": "32 inch QHD 240Hz",
                    "os": "Windows",
                },
            },
            {
                "name": "Dell UltraSharp U2723QE",
                "brand": "Dell",
                "price": 14990000,
                "description": "Màn hình 4K chuẩn màu cho đồ họa và chỉnh sửa ảnh video.",
                "image": "https://images.unsplash.com/photo-1517059224940-d4af9eec41b7?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "27 inch 4K",
                    "os": "Windows/macOS",
                },
            },
            {
                "name": "ASUS ProArt PA279CV",
                "brand": "ASUS",
                "price": 10990000,
                "description": "Màn hình ProArt cho creator với độ phủ màu cao.",
                "image": "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "27 inch 4K",
                    "os": "Windows/macOS",
                },
            },
            {
                "name": "AOC 24G2SP",
                "brand": "AOC",
                "price": 4590000,
                "description": "Màn hình gaming 24 inch 165Hz giá tốt cho setup phổ thông.",
                "image": "https://images.unsplash.com/photo-1616763355548-1b606f439f86?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "FreeSync",
                    "screen_size": "24 inch FHD 165Hz",
                    "os": "Windows",
                },
            },
            {
                "name": "BenQ GW2780",
                "brand": "BenQ",
                "price": 4190000,
                "description": "Màn hình văn phòng 27 inch chống chói, bảo vệ mắt.",
                "image": "https://images.unsplash.com/photo-1587202372616-b43abea06c2a?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "27 inch FHD",
                    "os": "Windows/macOS",
                },
            },
        ],
    },
    "accessory": {
        "resource": "accessories",
        "categories": [
            ("Ốp lưng", "Ốp bảo vệ điện thoại"),
            ("Kính cường lực", "Bảo vệ màn hình"),
            ("Gimbal & tripod", "Phụ kiện quay chụp di động"),
        ],
        "products": [
            {
                "name": "Spigen Rugged Armor for iPhone 15 Pro",
                "brand": "Spigen",
                "price": 590000,
                "description": "Ốp lưng chống sốc mỏng nhẹ, bảo vệ tốt cho iPhone.",
                "image": "https://images.unsplash.com/photo-1580910051074-3eb694886505?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "iPhone 15 Pro",
                    "os": "iOS",
                },
            },
            {
                "name": "UAG Pathfinder for Galaxy S24 Ultra",
                "brand": "UAG",
                "price": 990000,
                "description": "Ốp chống va đập đạt chuẩn quân đội cho Galaxy S24 Ultra.",
                "image": "https://images.unsplash.com/photo-1606041011872-596597976b25?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "Galaxy S24 Ultra",
                    "os": "Android",
                },
            },
            {
                "name": "Belkin TemperedGlass Ultra iPhone",
                "brand": "Belkin",
                "price": 490000,
                "description": "Kính cường lực độ trong cao, chống trầy xước tốt.",
                "image": "https://images.unsplash.com/photo-1512499617640-c2f999098c01?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "6.1 inch",
                    "os": "iOS",
                },
            },
            {
                "name": "Anker 3-in-1 MagSafe Stand",
                "brand": "Anker",
                "price": 2290000,
                "description": "Đế sạc kiêm giá đỡ MagSafe cho iPhone, AirPods và Apple Watch.",
                "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "3 thiết bị",
                    "os": "iOS",
                },
            },
            {
                "name": "DJI Osmo Mobile 6",
                "brand": "DJI",
                "price": 3290000,
                "description": "Gimbal chống rung 3 trục cho quay video bằng smartphone.",
                "image": "https://images.unsplash.com/photo-1522125670776-3c7abb882bc2?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "3-axis",
                    "os": "iOS/Android",
                },
            },
            {
                "name": "Ulanzi MT-44 Tripod",
                "brand": "Ulanzi",
                "price": 690000,
                "description": "Tripod gọn nhẹ cho vlog và livestream bằng điện thoại.",
                "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "1.5m",
                    "os": "Universal",
                },
            },
        ],
    },
    "charging": {
        "resource": "chargings",
        "categories": [
            ("Sạc nhanh", "Củ sạc công suất cao"),
            ("Pin dự phòng", "Dung lượng lớn cho di chuyển"),
            ("Sạc không dây", "Giải pháp sạc tiện lợi"),
        ],
        "products": [
            {
                "name": "Anker Nano II 65W GaN",
                "brand": "Anker",
                "price": 990000,
                "description": "Củ sạc GaN nhỏ gọn, hỗ trợ sạc nhanh cho laptop và điện thoại.",
                "image": "https://images.unsplash.com/photo-1583394838336-acd977736f90?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "GaN II",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "65W",
                    "os": "PD 3.0",
                },
            },
            {
                "name": "UGREEN Nexode 100W 4-Port",
                "brand": "UGREEN",
                "price": 1490000,
                "description": "Sạc đa cổng 100W phù hợp cho người dùng nhiều thiết bị.",
                "image": "https://images.unsplash.com/photo-1615526675159-e248f7f9524d?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "GaN",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "100W",
                    "os": "PD/QC",
                },
            },
            {
                "name": "Baseus Blade 10000mAh 65W",
                "brand": "Baseus",
                "price": 1590000,
                "description": "Pin dự phòng mỏng nhẹ, hỗ trợ sạc nhanh PD 65W.",
                "image": "https://images.unsplash.com/photo-1609592806596-4d4d8f6f1baf?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "10000mAh",
                    "gpu": "N/A",
                    "screen_size": "65W",
                    "os": "PD 3.0",
                },
            },
            {
                "name": "Anker PowerCore 20000 20W",
                "brand": "Anker",
                "price": 1190000,
                "description": "Pin dự phòng dung lượng lớn cho nhu cầu di chuyển dài ngày.",
                "image": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "20000mAh",
                    "gpu": "N/A",
                    "screen_size": "20W",
                    "os": "QC/PD",
                },
            },
            {
                "name": "Belkin BoostCharge Pro MagSafe 15W",
                "brand": "Belkin",
                "price": 1390000,
                "description": "Đế sạc không dây MagSafe 15W cho bàn làm việc gọn gàng.",
                "image": "https://images.unsplash.com/photo-1622445275576-721325763afe?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "15W",
                    "os": "MagSafe",
                },
            },
            {
                "name": "Samsung Wireless Charger Duo",
                "brand": "Samsung",
                "price": 1690000,
                "description": "Sạc không dây đôi cho điện thoại và đồng hồ cùng lúc.",
                "image": "https://images.unsplash.com/photo-1586953208448-b95a79798f07?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "N/A",
                    "ram": "N/A",
                    "storage": "N/A",
                    "gpu": "N/A",
                    "screen_size": "2 thiết bị",
                    "os": "Qi",
                },
            },
        ],
    },
    "book": {
        "resource": "books",
        "categories": [
            ("Sách lập trình", "Tài liệu phát triển phần mềm"),
            ("Sách sản phẩm", "Thiết kế và quản trị sản phẩm"),
            ("Sách kỹ năng", "Tư duy và kỹ năng làm việc"),
        ],
        "products": [
            {
                "name": "Clean Code (Robert C. Martin)",
                "brand": "Pearson",
                "price": 489000,
                "description": "Cuốn sách kinh điển về cách viết code sạch và dễ bảo trì.",
                "image": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Sách giấy",
                    "ram": "464 trang",
                    "storage": "English",
                    "gpu": "Bìa mềm",
                    "screen_size": "Khổ 17x24cm",
                    "os": "N/A",
                },
            },
            {
                "name": "Designing Data-Intensive Applications",
                "brand": "O'Reilly",
                "price": 799000,
                "description": "Nền tảng thiết kế hệ thống dữ liệu hiện đại cho backend engineer.",
                "image": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Sách giấy",
                    "ram": "616 trang",
                    "storage": "English",
                    "gpu": "Bìa mềm",
                    "screen_size": "Khổ 17x24cm",
                    "os": "N/A",
                },
            },
            {
                "name": "System Design Interview Vol.1",
                "brand": "ByteByteGo",
                "price": 599000,
                "description": "Tổng hợp các bài toán thiết kế hệ thống phổ biến trong phỏng vấn.",
                "image": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Sách giấy",
                    "ram": "322 trang",
                    "storage": "English",
                    "gpu": "Bìa mềm",
                    "screen_size": "Khổ 16x24cm",
                    "os": "N/A",
                },
            },
            {
                "name": "Hooked - How to Build Habit-Forming Products",
                "brand": "Portfolio",
                "price": 329000,
                "description": "Sách về product growth, hành vi người dùng và thiết kế trải nghiệm.",
                "image": "https://images.unsplash.com/photo-1473755504818-b72b6dfdc226?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Sách giấy",
                    "ram": "256 trang",
                    "storage": "English",
                    "gpu": "Bìa mềm",
                    "screen_size": "Khổ 14x20cm",
                    "os": "N/A",
                },
            },
            {
                "name": "Atomic Habits",
                "brand": "Avery",
                "price": 289000,
                "description": "Phương pháp xây dựng thói quen tốt và cải thiện hiệu suất cá nhân.",
                "image": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Sách giấy",
                    "ram": "320 trang",
                    "storage": "English",
                    "gpu": "Bìa mềm",
                    "screen_size": "Khổ 14x20cm",
                    "os": "N/A",
                },
            },
            {
                "name": "The Pragmatic Programmer",
                "brand": "Addison-Wesley",
                "price": 549000,
                "description": "Sách kinh điển giúp nâng cấp tư duy và kỹ năng của lập trình viên chuyên nghiệp.",
                "image": "https://images.unsplash.com/photo-1513530176992-0cf39c4cbed4?auto=format&fit=crop&w=1200&q=80",
                "specs": {
                    "cpu": "Sách giấy",
                    "ram": "352 trang",
                    "storage": "English",
                    "gpu": "Bìa mềm",
                    "screen_size": "Khổ 17x24cm",
                    "os": "N/A",
                },
            },
        ],
    },
}


def ensure_extended_catalog(token: str) -> dict[str, list[int]]:
    seeded_ids: dict[str, list[int]] = {}

    status, payload = http_json("GET", "/api/catalog/categories/")
    if status != 200:
        raise RuntimeError(
            f"Cannot list catalog categories: HTTP {status} -> {payload}"
        )

    existing_categories = {
        item.get("name"): item.get("id") for item in payload if isinstance(item, dict)
    }

    for product_type, config in EXTENDED_CATALOG.items():
        category_ids: list[int] = []
        for category_name, category_desc in config["categories"]:
            category_id = existing_categories.get(category_name)
            if not category_id:
                c_status, c_payload = http_json(
                    "POST",
                    "/api/catalog/categories/",
                    {"name": category_name, "description": category_desc},
                    token=token,
                )
                if c_status not in (200, 201):
                    raise RuntimeError(
                        f"Create category '{category_name}' failed: HTTP {c_status} -> {c_payload}"
                    )
                category_id = c_payload.get("id")
                existing_categories[category_name] = category_id

            if isinstance(category_id, int):
                category_ids.append(category_id)

        if not category_ids:
            raise RuntimeError(f"No category IDs available for {product_type}")

        existing_names = get_existing_names(
            f"/api/catalog/products/?type={product_type}&page_size=300"
        )
        seeded_ids[product_type] = []

        for idx, product in enumerate(config["products"], 1):
            name = product["name"]
            if name in existing_names:
                seeded_ids[product_type].append(existing_names[name])
                continue

            payload = {
                "product_type": product_type,
                "name": name,
                "brand": product["brand"],
                "price": product["price"],
                "description": product["description"],
                "image": product["image"],
                "stock": 5 + (idx % 12),
                "category_id": category_ids[(idx - 1) % len(category_ids)],
                "specs": normalize_specs(product["specs"], COMPUTER_SPEC_LIMITS),
            }

            create_status, create_payload = http_json(
                "POST",
                "/api/catalog/products/",
                payload,
                token=token,
            )
            if create_status != 201:
                raise RuntimeError(
                    f"Create {product_type} '{name}' failed: HTTP {create_status} -> {create_payload}"
                )

            product_id = create_payload.get("id")
            if isinstance(product_id, int):
                seeded_ids[product_type].append(product_id)

    return seeded_ids


def backfill_missing_images(token: str) -> None:
    image_fallbacks = {
        "computer": "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=1200&q=80",
        "mobile": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
        "clothes": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=1200&q=80",
        "tablet": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1200&q=80",
        "audio": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=80",
        "wearable": "https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?auto=format&fit=crop&w=1200&q=80",
        "component": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80",
        "peripheral": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=1200&q=80",
        "monitor": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=1200&q=80",
        "accessory": "https://images.unsplash.com/photo-1606041011872-596597976b25?auto=format&fit=crop&w=1200&q=80",
        "charging": "https://images.unsplash.com/photo-1583394838336-acd977736f90?auto=format&fit=crop&w=1200&q=80",
        "book": "https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=1200&q=80",
    }

    product_types = [
        "computer",
        "mobile",
        "clothes",
        "tablet",
        "audio",
        "wearable",
        "component",
        "peripheral",
        "monitor",
        "accessory",
        "charging",
        "book",
    ]

    for product_type in product_types:
        status, payload = http_json(
            "GET", f"/api/catalog/products/?type={product_type}&page_size=300"
        )
        if status != 200:
            log(
                f"Warning: cannot read {product_type} for image backfill (HTTP {status})."
            )
            continue

        items = payload.get("results", []) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            item_id = item.get("id")
            image = str(item.get("image") or "").strip()
            if not isinstance(item_id, int) or image:
                continue

            patch_status, patch_payload = http_json(
                "PATCH",
                f"/api/catalog/products/{item_id}/",
                {"image": image_fallbacks[product_type]},
                token=token,
            )
            if patch_status not in (200, 202):
                log(
                    f"Warning: image backfill failed for {product_type}#{item_id}: HTTP {patch_status} -> {patch_payload}"
                )


def reset_product_catalog(token: str) -> None:
    log("Resetting existing catalog products before seeding...")

    status, payload = http_json("GET", "/api/catalog/products/?page_size=1000")
    if status != 200:
        raise RuntimeError(
            f"Cannot list existing catalog products for reset: HTTP {status} -> {payload}"
        )

    items = payload.get("results", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        items = []

    for item in items:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item_id, int):
            continue

        d_status, d_payload = http_json(
            "DELETE", f"/api/catalog/products/{item_id}/", token=token
        )
        if d_status not in (200, 202, 204, 404):
            raise RuntimeError(
                f"Delete catalog product #{item_id} failed: HTTP {d_status} -> {d_payload}"
            )


def seed_20_customers_and_orders() -> None:
    """Seed 20 extra customers and 20 orders directly in customer-service DB.

    Idempotent behavior:
    - customers are keyed by username prefix `customer_seed_XX`
    - orders are keyed by note prefix `SEED_ORDER_XX`
    """

    customer_service_code = """
from decimal import Decimal
from customers.models import Customer
from orders.models import Order, OrderItem

STATUS_FLOW = [
    "pending",
    "confirmed",
    "shipping",
    "completed",
    "cancelled",
]

def ensure_customer(idx):
    username = f"customer_seed_{idx:02d}"
    email = f"customer_seed_{idx:02d}@techstore.local"
    phone = f"091{idx:07d}"[:10]
    customer, _ = Customer.objects.get_or_create(
        username=username,
        defaults={
            "full_name": f"Seed Customer {idx:02d}",
            "email": email,
            "phone": phone,
            "address": f"{100 + idx} Nguyen Hue, District {(idx % 12) + 1}, HCMC",
        },
    )
    customer.full_name = f"Seed Customer {idx:02d}"
    customer.email = email
    customer.phone = phone
    customer.address = f"{100 + idx} Nguyen Hue, District {(idx % 12) + 1}, HCMC"
    customer.set_password(f"Customer{idx:02d}@123")
    customer.save()
    return customer

def ensure_order_for_customer(customer, idx):
    note = f"SEED_ORDER_{idx:02d}"
    existing = Order.objects.filter(note=note).first()
    if existing:
        return existing

    base_shipping = f"{200 + idx} Le Loi, Ward {(idx % 10) + 1}, HCMC"
    status = STATUS_FLOW[(idx - 1) % len(STATUS_FLOW)]

    order = Order.objects.create(
        customer_id=customer.id,
        shipping_address=base_shipping,
        phone=customer.phone,
        note=note,
        status=status,
        total_amount=Decimal("0"),
    )

    # Two line items per order for realistic test data.
    qty1 = (idx % 3) + 1
    qty2 = ((idx + 1) % 2) + 1
    price1 = Decimal(str(14500000 + idx * 250000))
    price2 = Decimal(str(8900000 + idx * 180000))

    item1 = OrderItem.objects.create(
        order=order,
        product_id=1000 + idx,
        product_type="computer" if idx % 2 == 0 else "mobile",
        product_name=f"SEED Item A {idx:02d}",
        quantity=qty1,
        price=price1,
    )
    item2 = OrderItem.objects.create(
        order=order,
        product_id=2000 + idx,
        product_type="mobile" if idx % 2 == 0 else "computer",
        product_name=f"SEED Item B {idx:02d}",
        quantity=qty2,
        price=price2,
    )

    total = (Decimal(item1.quantity) * item1.price) + (Decimal(item2.quantity) * item2.price)
    order.total_amount = total
    order.save(update_fields=["total_amount", "updated_at"])
    return order

seeded_customers = 0
seeded_orders = 0

for i in range(1, 21):
    customer = ensure_customer(i)
    seeded_customers += 1
    order = ensure_order_for_customer(customer, i)
    if order:
        seeded_orders += 1

print(f"SEEDED_CUSTOMERS={seeded_customers}")
print(f"SEEDED_ORDERS={seeded_orders}")
""".strip()

    run_compose_exec("customer-service", customer_service_code)


def seed_cart_for_customer(
    customer_token: str, laptop_ids: list[int], mobile_ids: list[int]
) -> None:
    status, payload = http_json(
        "GET", "/api/customer-service/cart/", token=customer_token
    )
    if status != 200:
        raise RuntimeError(f"Cannot load customer cart: {status} {payload}")

    items = payload.get("items", []) if isinstance(payload, dict) else []
    if items:
        log("Customer cart already has items, skipping cart seed.")
        return

    targets: list[tuple[str, int, int]] = []
    if laptop_ids:
        targets.append(("computer", laptop_ids[0], 1))
    if len(laptop_ids) > 1:
        targets.append(("computer", laptop_ids[1], 2))
    if mobile_ids:
        targets.append(("mobile", mobile_ids[0], 1))

    for product_type, product_id, quantity in targets:
        status, response = http_json(
            "POST",
            "/api/customer-service/cart/items/",
            {
                "product_id": product_id,
                "product_type": product_type,
                "quantity": quantity,
            },
            token=customer_token,
        )
        if status not in (200, 201):
            raise RuntimeError(
                f"Add to cart failed for {product_type}#{product_id}: {status} {response}"
            )


def print_summary() -> None:
    log("\nSeeding completed successfully.")
    log("Accounts for testing:")
    log(
        f"- Manager (admin role): {ACCOUNTS['manager']['username']} / {ACCOUNTS['manager']['password']}"
    )
    log(f"- Staff: {ACCOUNTS['staff']['username']} / {ACCOUNTS['staff']['password']}")
    log(
        f"- Customer: {ACCOUNTS['customer']['username']} / {ACCOUNTS['customer']['password']}"
    )


def main() -> int:
    try:
        log("Waiting for gateway...")
        wait_for_gateway()

        bootstrap_accounts_direct_db()

        manager_token = login_staff(
            ACCOUNTS["manager"]["username"], ACCOUNTS["manager"]["password"]
        )
        customer_token = login_customer(
            ACCOUNTS["customer"]["username"], ACCOUNTS["customer"]["password"]
        )

        if RESET_PRODUCT_CATALOG:
            reset_product_catalog(manager_token)
        else:
            log(
                "Catalog reset disabled (set RESET_PRODUCT_CATALOG=true to recreate catalog from scratch)."
            )

        computer_cat_ids, mobile_cat_ids, clothes_cat_ids = ensure_categories(
            manager_token
        )
        if not computer_cat_ids or not mobile_cat_ids or not clothes_cat_ids:
            raise RuntimeError("Category seed failed: category IDs missing")

        laptop_ids = ensure_30_laptops(manager_token, computer_cat_ids)
        mobile_ids = ensure_30_mobiles(manager_token, mobile_cat_ids)
        clothes_ids = ensure_50_clothes(manager_token, clothes_cat_ids)

        if SEED_EXTENDED_PRODUCTS:
            ensure_extended_catalog(manager_token)
        else:
            log(
                "Extended catalog seeding disabled (set SEED_EXTENDED_PRODUCTS=true to enable)."
            )

        backfill_missing_images(manager_token)

        if SEED_CUSTOMERS_ORDERS:
            seed_20_customers_and_orders()
        else:
            log(
                "Customers/orders seeding disabled (set SEED_CUSTOMERS_ORDERS=true to enable)."
            )

        if SEED_CART:
            try:
                seed_cart_for_customer(customer_token, laptop_ids, mobile_ids)
            except Exception as cart_exc:  # pylint: disable=broad-except
                log(f"Warning: cart seed skipped due to error: {cart_exc}")
        else:
            log("Cart seeding disabled (set SEED_CART=true to enable).")

        print_summary()
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        log(f"Seeding failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
