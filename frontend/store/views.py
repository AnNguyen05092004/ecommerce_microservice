import json
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt


PRODUCT_TYPE_CONFIG = {
    "computer": {
        "label": "Laptop",
        "badge": "Laptop",
    },
    "mobile": {
        "label": "Điện thoại",
        "badge": "Mobile",
    },
    "clothes": {
        "label": "Quần áo",
        "badge": "Quần áo",
    },
    "tablet": {
        "label": "Tablet",
        "badge": "Tablet",
    },
    "audio": {
        "label": "Âm thanh",
        "badge": "Audio",
    },
    "wearable": {
        "label": "Wearable",
        "badge": "Wearable",
    },
    "component": {
        "label": "Linh kiện",
        "badge": "Component",
    },
    "peripheral": {
        "label": "Phụ kiện PC",
        "badge": "Peripheral",
    },
    "monitor": {
        "label": "Màn hình",
        "badge": "Monitor",
    },
    "accessory": {
        "label": "Phụ kiện điện thoại",
        "badge": "Accessory",
    },
    "charging": {
        "label": "Sạc và pin",
        "badge": "Charging",
    },
    "book": {
        "label": "Sách",
        "badge": "Book",
    },
}


FALLBACK_PRODUCTS = [
    {
        "id": 9001,
        "product_type": "computer",
        "name": "MacBook Pro 16 inch M3 Max",
        "brand": "Apple",
        "price": "89.990.000đ",
        "price_value": 89990000,
        "old_price": "99.990.000đ",
        "rating": 4.9,
        "reviews": 234,
        "badge": "HOT",
        "stock": 12,
        "created_at": "2026-03-01T10:00:00+07:00",
        "category": {"id": 1, "name": "Laptop cao cap"},
        "description": "Laptop hieu nang cao cho cong viec sang tao va xu ly nang.",
        "specs": {
            "cpu": "Apple M3 Max",
            "ram": "32GB",
            "storage": "1TB SSD",
            "gpu": "Apple GPU",
            "screen_size": "16 inch",
            "os": "macOS",
        },
        "image": "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "id": 9002,
        "product_type": "mobile",
        "name": "iPhone 15 Pro Max 256GB",
        "brand": "Apple",
        "price": "32.990.000đ",
        "price_value": 32990000,
        "old_price": "35.990.000đ",
        "rating": 4.8,
        "reviews": 567,
        "badge": "SALE",
        "stock": 7,
        "created_at": "2026-03-08T10:00:00+07:00",
        "category": {"id": 1, "name": "Flagship"},
        "description": "Smartphone flagship camera manh va hieu nang vuot troi.",
        "specs": {
            "screen_size": "6.7 inch",
            "battery": "4422mAh",
            "camera": "48MP",
            "storage": "256GB",
            "ram": "8GB",
            "os": "iOS",
        },
        "image": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "id": 9003,
        "product_type": "computer",
        "name": "Dell XPS 15 OLED",
        "brand": "Dell",
        "price": "54.990.000đ",
        "price_value": 54990000,
        "old_price": "59.990.000đ",
        "rating": 4.7,
        "reviews": 189,
        "badge": "HOT",
        "stock": 9,
        "created_at": "2026-03-05T10:00:00+07:00",
        "category": {"id": 1, "name": "Laptop cao cap"},
        "description": "Laptop man hinh OLED, thiet ke gon nhe va hieu nang on dinh.",
        "specs": {
            "cpu": "Intel Core Ultra 7",
            "ram": "16GB",
            "storage": "1TB SSD",
            "gpu": "NVIDIA RTX 4050",
            "screen_size": "15.6 inch OLED",
            "os": "Windows 11",
        },
        "image": "https://images.unsplash.com/photo-1484788984921-03950022c9ef?auto=format&fit=crop&w=1200&q=80",
    },
    {
        "id": 9004,
        "product_type": "clothes",
        "name": "Áo thun Basic Premium",
        "brand": "H&M",
        "price": "199.000đ",
        "price_value": 199000,
        "old_price": "250.000đ",
        "rating": 4.6,
        "reviews": 310,
        "badge": "SALE",
        "stock": 100,
        "created_at": "2026-03-10T10:00:00+07:00",
        "category": {"id": 1, "name": "Áo thun"},
        "description": "Áo thun cotton 100% thoáng mát, phù hợp mặc hàng ngày.",
        "specs": {
            "size": "M",
            "color": "Trắng",
            "material": "Cotton 100%",
        },
        "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=1200&q=80",
    },
]


def _format_vnd(value):
    try:
        amount = float(value)
        return f"{amount:,.0f}".replace(",", ".") + "đ"
    except (TypeError, ValueError):
        return "Liên hệ"


def _fetch_list(path):
    url = f"{settings.GATEWAY_URL}{path}"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code != 200:
            return []
        payload = response.json()
        if isinstance(payload, dict) and "results" in payload:
            return payload.get("results", [])
        if isinstance(payload, list):
            return payload
        return []
    except requests.RequestException:
        return []


def _fetch_paginated(path):
    url = f"{settings.GATEWAY_URL}{path}"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code != 200:
            return {"results": [], "next": None, "count": 0}
        payload = response.json()
        if isinstance(payload, dict):
            return {
                "results": payload.get("results", []) or [],
                "next": payload.get("next"),
                "count": payload.get("count", 0) or 0,
            }
        if isinstance(payload, list):
            return {"results": payload, "next": None, "count": len(payload)}
        return {"results": [], "next": None, "count": 0}
    except (requests.RequestException, ValueError):
        return {"results": [], "next": None, "count": 0}


def _fetch_catalog_products(query):
    params = {
        "type": query.get("type", "all"),
        "search": query.get("search", "").strip(),
        "brand": query.get("brand", "").strip(),
        "category": query.get("category", "").strip(),
        "price_min": query.get("price_min", ""),
        "price_max": query.get("price_max", ""),
        "ordering": query.get("ordering", "-created_at"),
        "page": 1,
        "page_size": 96,
    }
    return _fetch_paginated(f"/api/catalog/products/?{urlencode(params)}")


def _fetch_detail(path):
    url = f"{settings.GATEWAY_URL}{path}"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code != 200:
            return None
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return None
    except requests.RequestException:
        return None


def _customer_auth_headers(request):
    if request.session.get("auth_user_type") != "customer":
        return None
    token = request.session.get("auth_token", "")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _session_auth_headers(request):
    token = request.session.get("auth_token", "")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _fetch_list_auth(path, headers):
    url = f"{settings.GATEWAY_URL}{path}"
    try:
        response = requests.get(url, headers=headers or {}, timeout=5)
        if response.status_code != 200:
            return []
        payload = response.json()
        if isinstance(payload, dict) and "results" in payload:
            return payload.get("results", [])
        if isinstance(payload, list):
            return payload
        return []
    except (requests.RequestException, ValueError):
        return []


def _fetch_detail_auth(path, headers):
    url = f"{settings.GATEWAY_URL}{path}"
    try:
        response = requests.get(url, headers=headers or {}, timeout=5)
        if response.status_code != 200:
            return None
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return None
    except (requests.RequestException, ValueError):
        return None


def _fetch_html_auth(request, path):
    headers = _session_auth_headers(request) or {}
    try:
        response = requests.get(
            f"{settings.GATEWAY_URL}{path}",
            headers=headers,
            timeout=8,
        )
    except requests.RequestException:
        return None, "Khong the ket noi toi advisor service."

    if response.status_code != 200:
        return None, f"Khong the tai report AI ({response.status_code})."
    return response.text, ""


def _api_request_auth(request, method, path, payload=None):
    headers = _session_auth_headers(request)
    if not headers:
        return None, "Không tìm thấy phiên đăng nhập. Vui lòng đăng nhập lại."

    try:
        response = requests.request(
            method,
            f"{settings.GATEWAY_URL}{path}",
            headers=headers,
            json=payload,
            timeout=6,
        )
    except requests.RequestException:
        return None, "Không thể kết nối tới service. Thử lại sau."
    return response, ""


def _advisor_session_id(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key or "anonymous-session"


def _advisor_headers(request):
    headers = {"Content-Type": "application/json"}
    token = request.session.get("auth_token", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _advisor_track_event(request, event_type, **payload):
    body = {
        "session_id": _advisor_session_id(request),
        "event_type": event_type,
        "language": payload.pop("language", settings.LANGUAGE_CODE or "vi"),
        "metadata": payload.pop("metadata", {}),
    }
    body.update(payload)
    try:
        requests.post(
            f"{settings.GATEWAY_URL}/api/advisor-service/events/track/",
            json=body,
            headers=_advisor_headers(request),
            timeout=3,
        )
    except requests.RequestException:
        return False
    return True


def _fetch_advisor_recommendations(request, limit=4, product_type="", product_id=None):
    try:
        response = requests.post(
            f"{settings.GATEWAY_URL}/api/advisor-service/recommendations/",
            json={
                "session_id": _advisor_session_id(request),
                "limit": limit,
                "product_type": product_type,
                "product_id": product_id,
                "language": settings.LANGUAGE_CODE or "vi",
            },
            headers=_advisor_headers(request),
            timeout=5,
        )
        if response.status_code != 200:
            return {"results": [], "summary": {}}
        payload = response.json()
        if isinstance(payload, dict):
            return payload
    except (requests.RequestException, ValueError):
        return {"results": [], "summary": {}}
    return {"results": [], "summary": {}}


def _fetch_advisor_semantic_products(request, query, limit=48, product_type=""):
    try:
        response = requests.post(
            f"{settings.GATEWAY_URL}/api/advisor-service/search/semantic/",
            json={
                "query": query,
                "session_id": _advisor_session_id(request),
                "product_type": product_type,
                "language": settings.LANGUAGE_CODE or "vi",
                "limit": limit,
            },
            headers=_advisor_headers(request),
            timeout=8,
        )
        if response.status_code != 200:
            return {"results": [], "mode": "error"}
        payload = response.json()
        if isinstance(payload, dict):
            return payload
    except (requests.RequestException, ValueError):
        return {"results": [], "mode": "error"}
    return {"results": [], "mode": "error"}


def _normalize_advisor_products(items):
    normalized = []
    for item in items or []:
        product_id = item.get("id") or item.get("product_id")
        product_type = item.get("product_type") or "computer"
        if not product_id:
            continue

        # Skip stale recommendation links that no longer exist in catalog.
        detail = _fetch_detail(f"/api/catalog/products/{product_type}/{product_id}/")
        if not detail:
            continue

        normalized.append(
            {
                "id": product_id,
                "product_type": product_type,
                "name": item.get("name", "Sản phẩm"),
                "brand": item.get("brand", "TechStore"),
                "price": _format_vnd(item.get("price")),
                "image": item.get("image")
                or "https://images.unsplash.com/photo-1527443224154-c4e38a8d6d58?auto=format&fit=crop&w=1200&q=80",
                "reason": item.get("reason", "Gợi ý từ hành vi gần đây"),
                "detail_url": f"/products/{product_type}/{product_id}",
            }
        )
    return normalized


def _fetch_cart(request):
    headers = _customer_auth_headers(request)
    if not headers:
        return None

    try:
        response = requests.get(
            f"{settings.GATEWAY_URL}/api/customer-service/cart/",
            headers=headers,
            timeout=4,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _cart_item_count(cart_payload):
    if not isinstance(cart_payload, dict):
        return 0
    items = cart_payload.get("items") or []
    count = 0
    for item in items:
        try:
            count += int(item.get("quantity", 0))
        except (TypeError, ValueError):
            continue
    return count


def _auth_context(request):
    cart_payload = _fetch_cart(request)
    return {
        "auth_user_type": request.session.get("auth_user_type", ""),
        "auth_user_name": request.session.get("auth_user_name", ""),
        "cart_count": _cart_item_count(cart_payload),
    }


def _normalize_categories(items, product_type):
    normalized = []
    for item in items:
        cid = item.get("id")
        if cid is None:
            continue
        normalized.append(
            {
                "key": f"{product_type}:{cid}",
                "name": item.get("name", "Danh mục"),
                "type": product_type,
                "id": cid,
            }
        )
    return normalized


def _to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _filter_products(
    products,
    selected_category,
    price_min,
    price_max,
    search_term="",
    selected_brand="",
    stock_min=None,
    stock_max=None,
):
    category_type = ""
    category_id = None
    if selected_category and ":" in selected_category:
        category_type, raw_id = selected_category.split(":", 1)
        try:
            category_id = int(raw_id)
        except ValueError:
            category_id = None

    search_text = (search_term or "").strip().lower()
    brand_text = (selected_brand or "").strip().lower()

    filtered = []
    for item in products:
        price_value = _to_number(item.get("price"))
        stock_value = _to_number(item.get("stock"))
        if price_min is not None and (price_value is None or price_value < price_min):
            continue
        if price_max is not None and (price_value is None or price_value > price_max):
            continue
        if stock_min is not None and (stock_value is None or stock_value < stock_min):
            continue
        if stock_max is not None and (stock_value is None or stock_value > stock_max):
            continue

        if brand_text:
            item_brand = (item.get("brand") or "").strip().lower()
            if item_brand != brand_text:
                continue

        if search_text:
            category = item.get("category") or {}
            searchable_fields = [
                item.get("name", ""),
                item.get("brand", ""),
                category.get("name", ""),
            ]
            haystack = " ".join(str(field or "") for field in searchable_fields).lower()
            if search_text not in haystack:
                continue

        if category_id is not None:
            if item.get("product_type") != category_type:
                continue
            category = item.get("category") or {}
            if category.get("id") != category_id:
                continue

        filtered.append(item)

    return filtered


def _matches_product_filters(
    item,
    selected_category,
    price_min,
    price_max,
    search_term="",
    selected_brand="",
    stock_min=None,
    stock_max=None,
):
    return bool(
        _filter_products(
            [item],
            selected_category,
            price_min,
            price_max,
            search_term,
            selected_brand,
            stock_min,
            stock_max,
        )
    )


def _service_pages(ptype, cfg, page_size=12):
    page = 1
    while True:
        payload = _fetch_paginated(
            f"/api/catalog/products/?type={ptype}&page={page}&page_size={page_size}&ordering=-created_at"
        )
        rows = payload.get("results") or []
        if not rows:
            break

        normalized = _normalize_products(rows, cfg["badge"])
        for item in normalized:
            item["product_type"] = ptype

        yield normalized

        if not payload.get("next"):
            break
        page += 1


def _iter_filtered_service_items(
    ptype,
    cfg,
    selected_category,
    price_min,
    price_max,
    search,
    brand,
    stock_min,
    stock_max,
):
    for chunk in _service_pages(ptype, cfg):
        for item in chunk:
            if _matches_product_filters(
                item,
                selected_category,
                price_min,
                price_max,
                search,
                brand,
                stock_min,
                stock_max,
            ):
                yield item


def _merge_newest_products(
    selected_types,
    selected_category,
    price_min,
    price_max,
    search,
    brand,
    stock_min,
    stock_max,
    needed_count,
):
    iterators = {}
    current_items = {}

    for ptype in selected_types:
        cfg = PRODUCT_TYPE_CONFIG[ptype]
        iterator = _iter_filtered_service_items(
            ptype,
            cfg,
            selected_category,
            price_min,
            price_max,
            search,
            brand,
            stock_min,
            stock_max,
        )
        iterators[ptype] = iterator
        current_items[ptype] = next(iterator, None)

    merged = []
    while len(merged) < needed_count:
        available = {
            ptype: item for ptype, item in current_items.items() if item is not None
        }
        if not available:
            break

        chosen_type, chosen_item = max(
            available.items(), key=lambda pair: pair[1].get("created_at") or ""
        )
        merged.append(chosen_item)
        current_items[chosen_type] = next(iterators[chosen_type], None)

    return merged


def _sort_products(products, sort_by):
    if sort_by == "price_asc":
        return sorted(products, key=lambda p: p.get("price_value") or 0)
    if sort_by == "price_desc":
        return sorted(products, key=lambda p: p.get("price_value") or 0, reverse=True)
    if sort_by == "name_asc":
        return sorted(products, key=lambda p: (p.get("name") or "").lower())
    if sort_by == "name_desc":
        return sorted(
            products, key=lambda p: (p.get("name") or "").lower(), reverse=True
        )
    if sort_by == "stock_asc":
        return sorted(products, key=lambda p: p.get("stock") or 0)
    if sort_by == "stock_desc":
        return sorted(products, key=lambda p: p.get("stock") or 0, reverse=True)
    if sort_by == "oldest":
        return sorted(products, key=lambda p: p.get("created_at") or "")
    # newest default
    return sorted(products, key=lambda p: p.get("created_at") or "", reverse=True)


def _paginate_products(products, page, page_size=8):
    total = len(products)
    total_pages = max((total + page_size - 1) // page_size, 1)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": products[start:end],
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def _pagination_links(request_get, current_page, total_pages):
    pages = []
    if total_pages <= 7:
        pages = list(range(1, total_pages + 1))
    else:
        pages = [1]
        window_start = max(2, current_page - 1)
        window_end = min(total_pages - 1, current_page + 1)

        if window_start > 2:
            pages.append("ellipsis")

        pages.extend(range(window_start, window_end + 1))

        if window_end < total_pages - 1:
            pages.append("ellipsis")

        pages.append(total_pages)

    links = []
    for page_num in pages:
        if page_num == "ellipsis":
            links.append({"type": "ellipsis"})
            continue

        params = request_get.copy()
        params["page"] = str(page_num)
        links.append(
            {
                "type": "page",
                "page": page_num,
                "is_current": page_num == current_page,
                "query": urlencode(params, doseq=True),
            }
        )
    return links


def _build_gallery_images(primary_image):
    if not primary_image:
        return []
    if "images.unsplash.com" in primary_image:
        separator = "&" if "?" in primary_image else "?"
        return [
            primary_image,
            f"{primary_image}{separator}sat=-10",
            f"{primary_image}{separator}contrast=8",
        ]
    return [primary_image, primary_image, primary_image]


def _extract_api_error(response):
    try:
        payload = response.json()
        if isinstance(payload, dict):
            if payload.get("error"):
                return str(payload.get("error"))
            if payload.get("detail"):
                return str(payload.get("detail"))
    except ValueError:
        pass
    return "Không thể thêm vào giỏ hàng lúc này."


def _cart_api_request(request, method, path, payload=None):
    headers = _customer_auth_headers(request)
    if not headers:
        return None, "Bạn cần đăng nhập bằng tài khoản customer."

    try:
        response = requests.request(
            method,
            f"{settings.GATEWAY_URL}{path}",
            headers=headers,
            json=payload,
            timeout=5,
        )
    except requests.RequestException:
        return None, "Không thể kết nối cart service. Thử lại sau."

    return response, ""


def _normalize_cart_items(items):
    normalized = []
    for item in items:
        product_type = item.get("product_type") or "computer"
        pid = item.get("product_id") or 0
        normalized.append(
            {
                "id": item.get("id"),
                "product_id": pid,
                "product_type": product_type,
                "detail_url": f"/products/{product_type}/{pid}",
                "name": item.get("product_name") or "Sản phẩm",
                "image": item.get("product_image")
                or "https://images.unsplash.com/photo-1527443224154-c4e38a8d6d58?auto=format&fit=crop&w=1200&q=80",
                "quantity": item.get("quantity") or 1,
                "price": _format_vnd(item.get("price")),
                "subtotal": _format_vnd(item.get("subtotal")),
            }
        )
    return normalized


def _handle_add_to_cart(request, product_type, product_id):
    if request.session.get("auth_user_type") != "customer":
        return "error", "Bạn cần đăng nhập bằng tài khoản customer để thêm giỏ hàng."

    auth_token = request.session.get("auth_token", "")
    if not auth_token:
        return "error", "Không tìm thấy phiên đăng nhập. Vui lòng đăng nhập lại."

    quantity_raw = request.POST.get("quantity", "1")
    try:
        quantity = int(quantity_raw)
    except ValueError:
        quantity = 1
    quantity = max(1, min(quantity, 99))

    try:
        response = requests.post(
            f"{settings.GATEWAY_URL}/api/customer-service/cart/items/",
            json={
                "product_id": product_id,
                "product_type": product_type,
                "quantity": quantity,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=5,
        )
    except requests.RequestException:
        return "error", "Không thể kết nối đến giỏ hàng. Thử lại sau."

    if response.status_code in (200, 201):
        _advisor_track_event(
            request,
            "add_to_cart",
            product_type=product_type,
            product_id=product_id,
            quantity=quantity,
            metadata={"page": "product_detail"},
        )
        return "success", "Đã thêm sản phẩm vào giỏ hàng."
    return "error", _extract_api_error(response)


def _build_detail_context(product_type, product):
    display_type = PRODUCT_TYPE_CONFIG.get(product_type, {}).get("label", "Sản phẩm")
    gallery_images = _build_gallery_images(product.get("image", ""))

    context = {
        "product_type": product_type,
        "display_type": display_type,
        "product": product,
        "gallery_images": gallery_images,
        "breadcrumbs": [
            {"label": "Trang chủ", "url": "/"},
            {"label": "Sản phẩm", "url": "/products"},
            {"label": display_type, "url": f"/products?type={product_type}"},
            {"label": product.get("name", "Sản phẩm"), "url": ""},
        ],
    }
    return context


def _resolve_product_across_types(product_id):
    for ptype in PRODUCT_TYPE_CONFIG.keys():
        detail = _fetch_detail(f"/api/catalog/products/{ptype}/{product_id}/")
        if isinstance(detail, dict) and detail.get("id"):
            return ptype, detail
    return "", None


def _fetch_products_with_filters(query):
    product_type = query.get("type", "all")
    search = query.get("search", "").strip()
    brand = query.get("brand", "").strip()
    selected_category = query.get("category", "").strip()
    price_min = _to_number(query.get("price_min"))
    price_max = _to_number(query.get("price_max"))
    stock_min = _to_number(query.get("stock_min"))
    stock_max = _to_number(query.get("stock_max"))
    sort_by = query.get("sort", "newest")
    ordering_map = {
        "newest": "-created_at",
        "oldest": "created_at",
        "price_asc": "price",
        "price_desc": "-price",
        "name_asc": "name",
        "name_desc": "-name",
        "stock_asc": "stock",
        "stock_desc": "-stock",
    }
    catalog_query = query.copy()
    catalog_query["ordering"] = ordering_map.get(sort_by, "-created_at")
    payload = _fetch_catalog_products(catalog_query)

    cards = _normalize_semantic_products(payload.get("results"))

    cards = _filter_products(
        cards,
        selected_category,
        price_min,
        price_max,
        search,
        brand,
        stock_min,
        stock_max,
    )
    return _sort_products(cards, sort_by)


def _normalize_products(products, badge):
    normalized = []
    for item in products:
        normalized.append(
            {
                "id": item.get("id", 0),
                "name": item.get("name", "Sản phẩm công nghệ"),
                "brand": item.get("brand", "TechStore"),
                "price": _format_vnd(item.get("price")),
                "price_value": _to_number(item.get("price")),
                "old_price": "",
                "rating": 4.8,
                "reviews": 120,
                "badge": badge,
                "stock": item.get("stock", 0),
                "created_at": item.get("created_at", ""),
                "category": item.get("category") or {},
                "image": item.get("image")
                or "https://images.unsplash.com/photo-1527443224154-c4e38a8d6d58?auto=format&fit=crop&w=1200&q=80",
            }
        )
    return normalized


def _normalize_semantic_products(products):
    normalized = []
    for item in products or []:
        product_type = item.get("product_type") or "computer"
        badge = PRODUCT_TYPE_CONFIG.get(product_type, {}).get("badge", "AI")
        cards = _normalize_products([item], badge)
        if not cards:
            continue
        card = cards[0]
        card["product_type"] = product_type
        card["semantic_score"] = item.get("semantic_score", 0)
        card["reason"] = item.get("reason", "Ket qua semantic search")
        normalized.append(card)
    return normalized


def home_view(request):
    catalog_items = _fetch_list("/api/catalog/products/?page_size=8")
    computers = [p for p in catalog_items if p.get("product_type") == "computer"]
    mobiles = [p for p in catalog_items if p.get("product_type") == "mobile"]
    clothes_list = [p for p in catalog_items if p.get("product_type") == "clothes"]
    advisor_payload = _fetch_advisor_recommendations(request, limit=4)
    _advisor_track_event(request, "product_list_view", metadata={"page": "home"})

    product_cards = (
        _normalize_products(computers[:2], "HOT")
        + _normalize_products(mobiles[:1], "SALE")
        + _normalize_products(clothes_list[:1], "MỚI")
    )
    if not product_cards:
        product_cards = FALLBACK_PRODUCTS

    if len(product_cards) < 3:
        product_cards = product_cards + [
            p
            for p in FALLBACK_PRODUCTS
            if p.get("id") not in {x.get("id") for x in product_cards}
        ]

    context = {
        "featured_products": product_cards[:3],
        "advisor_recommendations": _normalize_advisor_products(
            advisor_payload.get("results")
        ),
        "advisor_summary": advisor_payload.get("summary") or {},
        "advisor_session_id": _advisor_session_id(request),
        "category_showcase": [
            {
                "name": "Công nghệ & Lập trình",
                "subtitle": "IT, Software, AI",
                "type": "book",
                "image": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Thiết bị di động",
                "subtitle": "Smartphone, Tablet",
                "type": "mobile",
                "image": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Gaming & Setup",
                "subtitle": "Linh kiện, Màn hình",
                "type": "component",
                "image": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Audio & Wearables",
                "subtitle": "Tai nghe, Đồng hồ thông minh",
                "type": "audio",
                "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Màn hình cao cấp",
                "subtitle": "4K, Ultrawide, Gaming",
                "type": "monitor",
                "image": "https://images.unsplash.com/photo-1527443224154-c4e38a8d6d58?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Phụ kiện điện thoại",
                "subtitle": "Ốp lưng, cáp, dock",
                "type": "accessory",
                "image": "https://images.unsplash.com/photo-1601972599720-36938d4ecd31?auto=format&fit=crop&w=1200&q=80",
            },
            {
                "name": "Sạc & Pin thông minh",
                "subtitle": "GaN charger, power bank",
                "type": "charging",
                "image": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=1200&q=80",
            },
        ],
        "category_cards": [
            {"name": "Laptop", "icon": "laptop"},
            {"name": "Điện thoại", "icon": "smartphone"},
            {"name": "Quần áo", "icon": "shirt"},
            {"name": "Tablet", "icon": "tablet"},
            {"name": "Audio", "icon": "headphones"},
            {"name": "Wearable", "icon": "watch"},
            {"name": "Linh kiện", "icon": "cpu"},
            {"name": "Màn hình", "icon": "monitor"},
            {"name": "Sạc & Pin", "icon": "battery-charging"},
        ],
    }
    context.update(_auth_context(request))
    return render(request, "store/home.html", context)


def _login_view(request, user_type):
    if request.method == "GET":
        context = {
            "login_type": user_type,
            "login_title": (
                "Đăng nhập Customer" if user_type == "customer" else "Đăng nhập Staff"
            ),
            "api_hint": (
                "customer-service" if user_type == "customer" else "staff-service"
            ),
            "error": "",
        }
        context.update(_auth_context(request))
        return render(request, "store/login.html", context)

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "").strip()

    if not username or not password:
        context = {
            "login_type": user_type,
            "login_title": (
                "Đăng nhập Customer" if user_type == "customer" else "Đăng nhập Staff"
            ),
            "api_hint": (
                "customer-service" if user_type == "customer" else "staff-service"
            ),
            "error": "Vui lòng nhập đầy đủ username và password.",
        }
        context.update(_auth_context(request))
        return render(request, "store/login.html", context)

    auth_path = (
        "/api/customer-service/auth/login/"
        if user_type == "customer"
        else "/api/staff-service/auth/login/"
    )
    try:
        response = requests.post(
            f"{settings.GATEWAY_URL}{auth_path}",
            json={"username": username, "password": password},
            timeout=5,
        )
    except requests.RequestException:
        response = None

    if not response or response.status_code != 200:
        context = {
            "login_type": user_type,
            "login_title": (
                "Đăng nhập Customer" if user_type == "customer" else "Đăng nhập Staff"
            ),
            "api_hint": (
                "customer-service" if user_type == "customer" else "staff-service"
            ),
            "error": "Đăng nhập thất bại. Vui lòng kiểm tra thông tin.",
        }
        context.update(_auth_context(request))
        return render(request, "store/login.html", context)

    payload = response.json()
    user_info = payload.get("user") or {}
    request.session["auth_token"] = payload.get("token", "")
    request.session["auth_user_type"] = user_type
    request.session["auth_user_name"] = (
        user_info.get("full_name") or user_info.get("username") or username
    )

    # Redirect staff users to dashboard, customers to products
    if user_type == "staff":
        return redirect("staff-dashboard")
    return redirect("products")


def customer_login_view(request):
    return _login_view(request, "customer")


def staff_login_view(request):
    return _login_view(request, "staff")


def logout_view(request):
    request.session.flush()
    return redirect("home")


def cart_view(request):
    if request.session.get("auth_user_type") != "customer":
        return redirect("customer-login")

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "checkout":
            shipping_address = request.POST.get("shipping_address", "").strip()
            phone = request.POST.get("phone", "").strip()
            note = request.POST.get("note", "").strip()

            if not shipping_address or not phone:
                query = urlencode(
                    {
                        "msg_type": "error",
                        "msg": "Vui lòng nhập địa chỉ giao hàng và số điện thoại.",
                    }
                )
                return redirect(f"/cart?{query}")

            response, error = _api_request_auth(
                request,
                "POST",
                "/api/customer-service/orders/",
                {
                    "shipping_address": shipping_address,
                    "phone": phone,
                    "note": note,
                },
            )
            if not response:
                query = urlencode({"msg_type": "error", "msg": error})
                return redirect(f"/cart?{query}")

            if response.status_code == 201:
                query = urlencode(
                    {"msg_type": "success", "msg": "Đặt hàng thành công."}
                )
                return redirect(f"/my-orders?{query}")

            query = urlencode(
                {"msg_type": "error", "msg": _extract_api_error(response)}
            )
            return redirect(f"/cart?{query}")

        item_id = request.POST.get("item_id", "")
        try:
            item_id_int = int(item_id)
        except ValueError:
            item_id_int = 0

        if item_id_int <= 0:
            query = urlencode(
                {"msg_type": "error", "msg": "Mục giỏ hàng không hợp lệ."}
            )
            return redirect(f"/cart?{query}")

        if action == "update":
            quantity_raw = request.POST.get("quantity", "1")
            try:
                quantity = int(quantity_raw)
            except ValueError:
                quantity = 1
            quantity = max(1, min(quantity, 99))

            response, error = _cart_api_request(
                request,
                "PUT",
                f"/api/customer-service/cart/items/{item_id_int}/",
                payload={"quantity": quantity},
            )
            if not response:
                query = urlencode({"msg_type": "error", "msg": error})
                return redirect(f"/cart?{query}")

            if response.status_code == 200:
                query = urlencode(
                    {"msg_type": "success", "msg": "Đã cập nhật số lượng."}
                )
                return redirect(f"/cart?{query}")

            query = urlencode(
                {"msg_type": "error", "msg": _extract_api_error(response)}
            )
            return redirect(f"/cart?{query}")

        if action == "delete":
            response, error = _cart_api_request(
                request,
                "DELETE",
                f"/api/customer-service/cart/items/{item_id_int}/",
            )
            if not response:
                query = urlencode({"msg_type": "error", "msg": error})
                return redirect(f"/cart?{query}")

            if response.status_code == 204:
                query = urlencode(
                    {"msg_type": "success", "msg": "Đã xóa sản phẩm khỏi giỏ."}
                )
                return redirect(f"/cart?{query}")

            query = urlencode(
                {"msg_type": "error", "msg": _extract_api_error(response)}
            )
            return redirect(f"/cart?{query}")

    cart_payload = _fetch_cart(request) or {"items": [], "total_amount": 0}
    items = _normalize_cart_items(cart_payload.get("items") or [])
    seed_product_type = ""
    seed_product_id = None
    if items:
        seed_product_type = items[0].get("product_type") or ""
        seed_product_id = items[0].get("product_id")

    advisor_payload = _fetch_advisor_recommendations(
        request,
        limit=4,
        product_type=seed_product_type,
        product_id=seed_product_id,
    )

    context = {
        "cart_items": items,
        "cart_total": _format_vnd(cart_payload.get("total_amount")),
        "cart_count": _cart_item_count(cart_payload),
        "flash_message": request.GET.get("msg", ""),
        "flash_type": request.GET.get("msg_type", ""),
        "advisor_recommendations": _normalize_advisor_products(
            advisor_payload.get("results")
        ),
        "advisor_summary": advisor_payload.get("summary") or {},
        "advisor_session_id": _advisor_session_id(request),
    }
    context.update(_auth_context(request))
    return render(request, "store/cart.html", context)


def products_view(request):
    selected_type = request.GET.get("type", "all")
    search_term = request.GET.get("search", "").strip()
    selected_brand = request.GET.get("brand", "").strip()
    selected_category = request.GET.get("category", "").strip()
    price_min = _to_number(request.GET.get("price_min"))
    price_max = _to_number(request.GET.get("price_max"))
    stock_min = _to_number(request.GET.get("stock_min"))
    stock_max = _to_number(request.GET.get("stock_max"))
    sort_by = request.GET.get("sort", "newest")

    semantic_search_mode = "disabled"
    if search_term:
        semantic_payload = _fetch_advisor_semantic_products(
            request,
            query=search_term,
            limit=96,
            product_type="" if selected_type == "all" else selected_type,
        )
        semantic_search_mode = semantic_payload.get("mode") or "error"
        products = _normalize_semantic_products(semantic_payload.get("results"))
        products = _filter_products(
            products,
            selected_category,
            price_min,
            price_max,
            "",
            selected_brand,
            stock_min,
            stock_max,
        )
        products = _sort_products(products, sort_by)
        # Only fall back to local when the semantic service itself is unavailable,
        # not when it simply returned no matches for the query.
        if not products and semantic_search_mode in (
            "error",
            "graph_unavailable",
            "graph_error",
        ):
            products = _fetch_products_with_filters(request.GET)
            semantic_search_mode = "fallback_local"
    else:
        products = _fetch_products_with_filters(request.GET)

    # Show FALLBACK_PRODUCTS only when no search term is active (avoid showing
    # unrelated hardcoded products for queries that legitimately found nothing).
    if not products and not search_term:
        fallback_type = selected_type
        if fallback_type in PRODUCT_TYPE_CONFIG:
            products = [
                p for p in FALLBACK_PRODUCTS if p.get("product_type") == fallback_type
            ]
        else:
            products = FALLBACK_PRODUCTS.copy()
    page_raw = request.GET.get("page", "1")
    try:
        page = int(page_raw)
    except ValueError:
        page = 1

    paginated = _paginate_products(products, page, page_size=8)
    raw_cats = _fetch_list("/api/catalog/categories/")
    effective_type = (
        selected_type if selected_type and selected_type != "all" else "all"
    )
    categories = _normalize_categories(raw_cats, effective_type)

    brands = sorted({p.get("brand", "") for p in products if p.get("brand")})
    pagination_links = _pagination_links(
        request.GET, paginated["page"], paginated["total_pages"]
    )

    prev_query = ""
    if paginated["has_prev"]:
        prev_params = request.GET.copy()
        prev_params["page"] = str(paginated["page"] - 1)
        prev_query = urlencode(prev_params, doseq=True)

    next_query = ""
    if paginated["has_next"]:
        next_params = request.GET.copy()
        next_params["page"] = str(paginated["page"] + 1)
        next_query = urlencode(next_params, doseq=True)

    _advisor_track_event(
        request,
        "search" if search_term else "product_list_view",
        product_type="" if selected_type == "all" else selected_type,
        query_text=search_term,
        metadata={
            "page": "products",
            "sort": request.GET.get("sort", "newest"),
            "filters": {
                "brand": request.GET.get("brand", ""),
                "category": request.GET.get("category", ""),
                "price_min": request.GET.get("price_min", ""),
                "price_max": request.GET.get("price_max", ""),
            },
        },
    )

    advisor_payload = _fetch_advisor_recommendations(
        request,
        limit=6,
        product_type="" if selected_type == "all" else selected_type,
    )

    context = {
        "products": paginated["items"],
        "total_products": paginated["total"],
        "brands": brands,
        "categories": categories,
        "selected_type": selected_type,
        "selected_search": request.GET.get("search", ""),
        "selected_brand": request.GET.get("brand", ""),
        "selected_category": request.GET.get("category", ""),
        "selected_price_min": request.GET.get("price_min", ""),
        "selected_price_max": request.GET.get("price_max", ""),
        "selected_stock_min": request.GET.get("stock_min", ""),
        "selected_stock_max": request.GET.get("stock_max", ""),
        "selected_sort": request.GET.get("sort", "newest"),
        "semantic_search_mode": semantic_search_mode,
        "current_page": paginated["page"],
        "total_pages": paginated["total_pages"],
        "pagination_links": pagination_links,
        "has_prev": paginated["has_prev"],
        "has_next": paginated["has_next"],
        "prev_query": prev_query,
        "next_query": next_query,
        "advisor_recommendations": _normalize_advisor_products(
            advisor_payload.get("results")
        ),
        "advisor_summary": advisor_payload.get("summary") or {},
        "advisor_session_id": _advisor_session_id(request),
    }
    context.update(_auth_context(request))
    return render(request, "store/products.html", context)


def product_detail_view(request, product_type, product_id):
    if product_type not in PRODUCT_TYPE_CONFIG:
        raise Http404("Product type not supported")

    if request.method == "POST" and request.POST.get("action") == "add_to_cart":
        msg_type, msg = _handle_add_to_cart(request, product_type, product_id)
        query = urlencode({"msg_type": msg_type, "msg": msg})
        return redirect(f"/products/{product_type}/{product_id}?{query}")

    flash_message = request.GET.get("msg", "")
    flash_type = request.GET.get("msg_type", "")

    detail_path = f"/api/catalog/products/{product_type}/{product_id}/"
    product = _fetch_detail(detail_path)
    if not product:
        resolved_type, resolved_product = _resolve_product_across_types(product_id)
        if resolved_product and resolved_type:
            if request.method == "POST":
                query = urlencode(
                    {
                        "msg_type": "error",
                        "msg": "San pham da duoc chuyen sang nhom khac.",
                    }
                )
                return redirect(f"/products/{resolved_type}/{product_id}?{query}")
            return redirect(f"/products/{resolved_type}/{product_id}")

        fallback_product = next(
            (
                p
                for p in FALLBACK_PRODUCTS
                if p.get("product_type") == product_type and p.get("id") == product_id
            ),
            None,
        )
        if fallback_product:
            context = _build_detail_context(
                product_type,
                {
                    "id": fallback_product.get("id", 0),
                    "name": fallback_product.get("name", "Sản phẩm"),
                    "brand": fallback_product.get("brand", "TechStore"),
                    "price": fallback_product.get("price", "Liên hệ"),
                    "stock": fallback_product.get("stock", 0),
                    "status": "available",
                    "description": fallback_product.get("description", ""),
                    "image": fallback_product.get("image", ""),
                    "category": (fallback_product.get("category") or {}).get(
                        "name", "Khác"
                    ),
                    "specs": fallback_product.get("specs") or {},
                },
            )
            context["flash_message"] = flash_message
            context["flash_type"] = flash_type
            context.update(_auth_context(request))
            return render(request, "store/product_detail.html", context)
        raise Http404("Product not found")

    context = _build_detail_context(
        product_type,
        {
            "id": product.get("id", 0),
            "name": product.get("name", "Sản phẩm"),
            "brand": product.get("brand", "TechStore"),
            "price": _format_vnd(product.get("price")),
            "stock": product.get("stock", 0),
            "status": product.get("status", "available"),
            "description": product.get("description", ""),
            "image": product.get("image")
            or "https://images.unsplash.com/photo-1527443224154-c4e38a8d6d58?auto=format&fit=crop&w=1200&q=80",
            "category": (product.get("category") or {}).get("name", "Khác"),
            "specs": product.get("specs") or {},
        },
    )
    review_rows = _fetch_list(
        f"/api/customer-service/reviews/?product_id={product_id}&product_type={product_type}&page_size=20"
    )
    advisor_payload = _fetch_advisor_recommendations(
        request, limit=4, product_type=product_type, product_id=product_id
    )
    _advisor_track_event(
        request,
        "product_detail_view",
        product_type=product_type,
        product_id=product_id,
        metadata={"page": "product_detail", "product_name": product.get("name", "")},
    )
    context["reviews"] = review_rows if isinstance(review_rows, list) else []
    context["advisor_recommendations"] = _normalize_advisor_products(
        advisor_payload.get("results")
    )
    context["advisor_summary"] = advisor_payload.get("summary") or {}
    context["advisor_session_id"] = _advisor_session_id(request)
    context["advisor_debug_panel"] = bool(
        getattr(settings, "ADVISOR_DEBUG_PANEL", False)
    )
    context["flash_message"] = flash_message
    context["flash_type"] = flash_type
    context.update(_auth_context(request))
    return render(request, "store/product_detail.html", context)


@csrf_exempt
def advisor_chat_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    try:
        response = requests.post(
            f"{settings.GATEWAY_URL}/api/advisor-service/chat/",
            json={
                "message": payload.get("message", ""),
                "session_id": _advisor_session_id(request),
                "language": payload.get("language", settings.LANGUAGE_CODE or "vi"),
                "product_type": payload.get("product_type", ""),
                "product_id": payload.get("product_id"),
            },
            headers=_advisor_headers(request),
            timeout=20,
        )
    except requests.RequestException:
        return JsonResponse({"error": "Advisor service unavailable"}, status=503)

    try:
        body = response.json()
    except ValueError:
        return JsonResponse({"error": "Invalid advisor response"}, status=502)
    return JsonResponse(body, status=response.status_code)


@csrf_exempt
def advisor_event_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    success = _advisor_track_event(
        request,
        payload.get("event_type", "chat_open"),
        product_type=payload.get("product_type", ""),
        product_id=payload.get("product_id"),
        query_text=payload.get("query_text", ""),
        metadata=payload.get("metadata", {}),
        language=payload.get("language", settings.LANGUAGE_CODE or "vi"),
    )
    return JsonResponse({"status": "ok" if success else "ignored"})


@csrf_exempt
def advisor_keyword_suggest_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    prefix = (payload.get("prefix") or "").strip()
    if len(prefix) < 2:
        return JsonResponse({"results": []})

    try:
        response = requests.post(
            f"{settings.GATEWAY_URL}/api/advisor-service/search/suggest/",
            json={
                "prefix": prefix,
                "session_id": _advisor_session_id(request),
                "language": payload.get("language", settings.LANGUAGE_CODE or "vi"),
                "product_type": payload.get("product_type", ""),
                "limit": payload.get("limit", 5),
            },
            headers=_advisor_headers(request),
            timeout=6,
        )
    except requests.RequestException:
        return JsonResponse({"results": []})

    try:
        body = response.json()
    except ValueError:
        return JsonResponse({"results": []})

    suggestions = body.get("results") if isinstance(body, dict) else []
    if not isinstance(suggestions, list):
        suggestions = []
    return JsonResponse({"results": suggestions[:8]}, status=200)


@csrf_exempt
def advisor_semantic_search_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body"}, status=400)

    query = (payload.get("query") or "").strip()
    if len(query) < 2:
        return JsonResponse({"results": [], "mode": "too_short"}, status=200)

    try:
        response = requests.post(
            f"{settings.GATEWAY_URL}/api/advisor-service/search/semantic/",
            json={
                "query": query,
                "session_id": _advisor_session_id(request),
                "language": payload.get("language", settings.LANGUAGE_CODE or "vi"),
                "product_type": payload.get("product_type", ""),
                "limit": payload.get("limit", 6),
            },
            headers=_advisor_headers(request),
            timeout=8,
        )
    except requests.RequestException:
        return JsonResponse({"results": [], "mode": "service_unavailable"}, status=503)

    try:
        body = response.json()
    except ValueError:
        return JsonResponse({"results": [], "mode": "invalid_response"}, status=502)

    if not isinstance(body, dict):
        return JsonResponse({"results": [], "mode": "invalid_response"}, status=502)
    return JsonResponse(body, status=response.status_code)


def customer_orders_view(request):
    if request.session.get("auth_user_type") != "customer":
        return redirect("customer-login")

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "create_review":
            product_id_raw = request.POST.get("product_id", "0")
            product_type = request.POST.get("product_type", "").strip()
            rating_raw = request.POST.get("rating", "0")
            comment = request.POST.get("comment", "").strip()

            try:
                product_id = int(product_id_raw)
                rating = int(rating_raw)
            except ValueError:
                query = urlencode(
                    {
                        "msg_type": "error",
                        "msg": "Dữ liệu đánh giá không hợp lệ.",
                    }
                )
                return redirect(f"/my-orders?{query}")

            if product_type not in PRODUCT_TYPE_CONFIG or not (1 <= rating <= 5):
                query = urlencode(
                    {"msg_type": "error", "msg": "Thông tin đánh giá không hợp lệ."}
                )
                return redirect(f"/my-orders?{query}")

            response, error = _api_request_auth(
                request,
                "POST",
                "/api/customer-service/reviews/",
                {
                    "product_id": product_id,
                    "product_type": product_type,
                    "rating": rating,
                    "comment": comment,
                },
            )
            if not response:
                query = urlencode({"msg_type": "error", "msg": error})
                return redirect(f"/my-orders?{query}")

            if response.status_code == 201:
                query = urlencode(
                    {"msg_type": "success", "msg": "Đánh giá sản phẩm thành công."}
                )
                return redirect(f"/my-orders?{query}")

            query = urlencode(
                {"msg_type": "error", "msg": _extract_api_error(response)}
            )
            return redirect(f"/my-orders?{query}")

    headers = _session_auth_headers(request) or {}
    status_filter = request.GET.get("status", "").strip()
    path = "/api/customer-service/orders/?page_size=50"
    if status_filter:
        path += f"&status={status_filter}"

    base_orders = _fetch_list_auth(path, headers)
    detailed_orders = []
    status_labels = {
        "pending": "Chờ xác nhận",
        "confirmed": "Đã xác nhận",
        "shipping": "Đang giao",
        "completed": "Hoàn thành",
        "cancelled": "Đã hủy",
    }
    for order in base_orders:
        oid = order.get("id")
        if not isinstance(oid, int):
            continue
        detail = _fetch_detail_auth(f"/api/customer-service/orders/{oid}/", headers)
        if isinstance(detail, dict):
            detail["status_label"] = status_labels.get(
                detail.get("status", ""), detail.get("status", "")
            )
            detailed_orders.append(detail)

    context = {
        "orders": detailed_orders,
        "selected_status": status_filter,
        "flash_message": request.GET.get("msg", ""),
        "flash_type": request.GET.get("msg_type", ""),
    }
    context.update(_auth_context(request))
    return render(request, "store/my_orders.html", context)


def _apply_staff_stock_filter_and_sort(products, stock_min, stock_max, sort_by):
    rows = []
    for item in products:
        stock = _to_number(item.get("stock"))
        if stock_min is not None and (stock is None or stock < stock_min):
            continue
        if stock_max is not None and (stock is None or stock > stock_max):
            continue
        rows.append(item)

    if sort_by == "stock_asc":
        return sorted(rows, key=lambda p: p.get("stock") or 0)
    if sort_by == "stock_desc":
        return sorted(rows, key=lambda p: p.get("stock") or 0, reverse=True)
    if sort_by == "name_asc":
        return sorted(rows, key=lambda p: (p.get("name") or "").lower())
    if sort_by == "name_desc":
        return sorted(rows, key=lambda p: (p.get("name") or "").lower(), reverse=True)
    if sort_by == "price_asc":
        return sorted(rows, key=lambda p: _to_number(p.get("price")) or 0)
    if sort_by == "price_desc":
        return sorted(rows, key=lambda p: _to_number(p.get("price")) or 0, reverse=True)
    return sorted(rows, key=lambda p: p.get("created_at") or "", reverse=True)


# ==================== STAFF VIEWS ====================


def _staff_auth_headers(request):
    """Check if user is logged in as staff and return auth headers."""
    if request.session.get("auth_user_type") != "staff":
        return None
    token = request.session.get("auth_token", "")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _staff_required(view_func):
    """Decorator to ensure only staff users can access a view."""

    def wrapper(request, *args, **kwargs):
        if request.session.get("auth_user_type") != "staff":
            return redirect("staff-login")
        return view_func(request, *args, **kwargs)

    return wrapper


@_staff_required
def staff_dashboard_view(request):
    """Staff dashboard home view with overview statistics."""
    headers = _staff_auth_headers(request)
    if not headers:
        return redirect("staff-login")

    # Fetch overview data
    product_counts = {}
    low_stock_items = []
    low_stock_by_type = {}
    for ptype in PRODUCT_TYPE_CONFIG.keys():
        rows = _fetch_list(f"/api/catalog/products/?type={ptype}&page_size=1000")
        rows = rows if isinstance(rows, list) else []
        product_counts[ptype] = len(rows)
        low_stock_by_type[ptype] = 0

        for item in rows:
            if item.get("stock", 0) < 5:
                low_stock_by_type[ptype] += 1
                low_stock_items.append(
                    {
                        "type": ptype,
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "stock": item.get("stock", 0),
                    }
                )

    orders = _fetch_list("/api/customer-service/orders/")

    # Calculate statistics
    total_computers = product_counts.get("computer", 0)
    total_mobiles = product_counts.get("mobile", 0)
    total_clothes = product_counts.get("clothes", 0)
    total_products = sum(product_counts.values())
    total_orders = len(orders) if isinstance(orders, list) else 0

    order_status_counts = {
        "pending": 0,
        "confirmed": 0,
        "shipping": 0,
        "completed": 0,
        "cancelled": 0,
    }
    if isinstance(orders, list):
        for order in orders:
            status_key = (order or {}).get("status", "")
            if status_key in order_status_counts:
                order_status_counts[status_key] += 1

    product_chart_labels = []
    product_chart_values = []
    for ptype, count in product_counts.items():
        if count <= 0:
            continue
        product_chart_labels.append(
            PRODUCT_TYPE_CONFIG.get(ptype, {}).get("label", ptype)
        )
        product_chart_values.append(count)

    low_stock_chart_labels = []
    low_stock_chart_values = []
    for ptype, count in low_stock_by_type.items():
        if count <= 0:
            continue
        low_stock_chart_labels.append(
            PRODUCT_TYPE_CONFIG.get(ptype, {}).get("label", ptype)
        )
        low_stock_chart_values.append(count)

    context = {
        "total_products": total_products,
        "total_computers": total_computers,
        "total_mobiles": total_mobiles,
        "total_clothes": total_clothes,
        "total_new_products": total_products
        - total_computers
        - total_mobiles
        - total_clothes,
        "total_orders": total_orders,
        "low_stock_items": low_stock_items[:10],
        "chart_product_labels": json.dumps(product_chart_labels, ensure_ascii=False),
        "chart_product_values": json.dumps(product_chart_values),
        "chart_low_stock_labels": json.dumps(
            low_stock_chart_labels, ensure_ascii=False
        ),
        "chart_low_stock_values": json.dumps(low_stock_chart_values),
        "chart_order_labels": json.dumps(
            ["Chờ xác nhận", "Đã xác nhận", "Đang giao", "Hoàn thành", "Đã hủy"],
            ensure_ascii=False,
        ),
        "chart_order_values": json.dumps(
            [
                order_status_counts["pending"],
                order_status_counts["confirmed"],
                order_status_counts["shipping"],
                order_status_counts["completed"],
                order_status_counts["cancelled"],
            ]
        ),
        "chart_kpi_labels": json.dumps(
            ["Tổng sản phẩm", "Đơn hàng", "Sắp hết hàng"], ensure_ascii=False
        ),
        "chart_kpi_values": json.dumps(
            [total_products, total_orders, len(low_stock_items)]
        ),
        "auth_user_name": request.session.get("auth_user_name", ""),
    }
    return render(request, "store/staff/dashboard.html", context)


@_staff_required
def staff_ai_metrics_view(request):
    """Staff-only AI metrics dashboard."""
    metrics_payload = _fetch_detail("/api/advisor-service/metrics/latest/") or {}
    health_payload = _fetch_detail("/api/advisor-service/ai/health/") or {}
    timeseries_payload = (
        _fetch_detail(
            "/api/advisor-service/metrics/timeseries/?operation=chat&window=1h"
        )
        or {}
    )

    metrics_data = metrics_payload.get("metrics") or {}
    latency = metrics_data.get("latency") or {}
    chat_latency = latency.get("chat") or {}
    recommend_latency = latency.get("recommendations") or {}

    errors = metrics_data.get("errors") or {}
    fallback = metrics_data.get("fallback") or {}
    events = list((timeseries_payload.get("points") or [])[-10:])[::-1]

    context = {
        "p95_chat_latency": chat_latency.get("p95", 0),
        "p95_recommend_latency": recommend_latency.get("p95", 0),
        "error_rate": metrics_data.get("error_rate", 0),
        "fallback_total": fallback.get("retrieval", 0) + fallback.get("baseline", 0),
        "health_status": health_payload.get("advisor_status")
        or metrics_payload.get("health", "unknown"),
        "llm_provider": (health_payload.get("llm") or {}).get("provider", "unknown"),
        "llm_model": (health_payload.get("llm") or {}).get("model", "unknown"),
        "behavior_model": (health_payload.get("behavior_model") or {}).get(
            "selected_model", "mlp"
        ),
        "behavior_model_score": (health_payload.get("behavior_model") or {}).get(
            "selected_model_score"
        ),
        "events": events,
        "metrics_raw": metrics_data,
        "errors_raw": errors,
        "auth_user_name": request.session.get("auth_user_name", ""),
    }
    return render(request, "store/admin/ai_metrics.html", context)


@_staff_required
def staff_ai_report_view(request, report_key):
    html, error = _fetch_html_auth(
        request,
        f"/api/advisor-service/ai/reports/{report_key}/",
    )
    if error:
        return HttpResponse(
            f"<html><body><h1>AI Report Unavailable</h1><p>{error}</p></body></html>",
            content_type="text/html; charset=utf-8",
            status=502,
        )
    return HttpResponse(html, content_type="text/html; charset=utf-8")


@_staff_required
def staff_products_computer_view(request):
    return _staff_products_generic_view(request, "computer")


@_staff_required
def staff_products_mobile_view(request):
    return _staff_products_generic_view(request, "mobile")


@_staff_required
def staff_orders_view(request):
    """Manage customer orders."""
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "update_status":
            order_id_raw = request.POST.get("order_id", "0")
            next_status = request.POST.get("status", "").strip()
            try:
                order_id = int(order_id_raw)
            except ValueError:
                order_id = 0

            allowed = {"confirmed", "shipping", "completed", "cancelled"}
            if order_id <= 0 or next_status not in allowed:
                query = urlencode(
                    {"error": "Du lieu cap nhat trang thai khong hop le."}
                )
                return redirect(f"/staff/orders?{query}")

            response, error = _api_request_auth(
                request,
                "PATCH",
                f"/api/customer-service/orders/{order_id}/status/",
                {"status": next_status},
            )
            if not response:
                query = urlencode({"error": error})
                return redirect(f"/staff/orders?{query}")

            if response.status_code == 200:
                query = urlencode({"msg": "Cap nhat trang thai don hang thanh cong."})
                return redirect(f"/staff/orders?{query}")

            query = urlencode({"error": _extract_api_error(response)})
            return redirect(f"/staff/orders?{query}")

    headers = _session_auth_headers(request) or {}
    selected_status = request.GET.get("status", "").strip()
    path = "/api/customer-service/orders/?page_size=200"
    if selected_status:
        path += f"&status={selected_status}"
    orders = _fetch_list_auth(path, headers)

    context = {
        "orders": orders if isinstance(orders, list) else [],
        "selected_status": selected_status,
        "message": request.GET.get("msg", ""),
        "error": request.GET.get("error", ""),
        "auth_user_name": request.session.get("auth_user_name", ""),
    }
    return render(request, "store/staff/orders.html", context)


@_staff_required
def staff_customers_view(request):
    """View and manage customers."""
    customers = _fetch_list("/api/customer-service/customers/?limit=1000")

    context = {
        "customers": customers if isinstance(customers, list) else [],
        "auth_user_name": request.session.get("auth_user_name", ""),
    }
    return render(request, "store/staff/customers.html", context)


@_staff_required
def staff_products_clothes_view(request):
    return _staff_products_generic_view(request, "clothes")


def _build_staff_product_payload(product_type, request):
    payload = {
        "product_type": product_type,
        "name": request.POST.get("name", ""),
        "brand": request.POST.get("brand", ""),
        "price": int(float(request.POST.get("price", 0))),
        "stock": int(request.POST.get("stock", 0)),
        "description": request.POST.get("description", ""),
        "category_id": int(request.POST.get("category", 0)),
        "image": request.POST.get("image", ""),
    }

    if product_type == "mobile":
        payload["specs"] = {
            "screen_size": request.POST.get("screen_size", ""),
            "battery": request.POST.get("battery", ""),
            "camera": request.POST.get("camera", ""),
            "storage": request.POST.get("storage", ""),
            "ram": request.POST.get("ram", ""),
            "os": request.POST.get("os", ""),
        }
    elif product_type == "clothes":
        payload["gender"] = request.POST.get("gender", "unisex")
        payload["specs"] = {
            "size": request.POST.get("size", ""),
            "color": request.POST.get("color", ""),
            "material": request.POST.get("material", ""),
        }
    else:
        payload["specs"] = {
            "cpu": request.POST.get("cpu", ""),
            "ram": request.POST.get("ram", ""),
            "storage": request.POST.get("storage", ""),
            "gpu": request.POST.get("gpu", ""),
            "screen_size": request.POST.get("screen_size", ""),
            "os": request.POST.get("os", ""),
        }

    return payload


def _staff_products_generic_view(request, product_type):
    cfg = PRODUCT_TYPE_CONFIG.get(product_type)
    if not cfg:
        raise Http404("Product type not supported")

    path = f"/staff/products/{product_type}"

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "quick_stock":
            product_id_raw = request.POST.get("product_id", "0")
            stock_raw = request.POST.get("stock", "0")
            try:
                product_id = int(product_id_raw)
                stock = int(stock_raw)
            except ValueError:
                query = urlencode({"error": "Dữ liệu số lượng không hợp lệ"})
                return redirect(f"{path}?{query}")

            if product_id <= 0 or stock < 0:
                query = urlencode({"error": "ID hoặc số lượng không hợp lệ"})
                return redirect(f"{path}?{query}")

            headers = _staff_auth_headers(request)
            if headers:
                try:
                    response = requests.patch(
                        f"{settings.GATEWAY_URL}/api/catalog/products/{product_id}/stock/",
                        json={"stock": stock},
                        headers=headers,
                        timeout=5,
                    )
                    if response.status_code == 200:
                        query = urlencode({"msg": "Đã cập nhật số lượng"})
                        return redirect(f"{path}?{query}")
                except requests.RequestException:
                    pass

            query = urlencode({"error": "Lỗi khi cập nhật số lượng"})
            return redirect(f"{path}?{query}")

        if action == "delete":
            product_id_raw = request.POST.get("product_id", "0")
            try:
                product_id = int(product_id_raw)
            except ValueError:
                product_id = 0

            if product_id <= 0:
                query = urlencode({"error": "ID sản phẩm không hợp lệ"})
                return redirect(f"{path}?{query}")

            headers = _staff_auth_headers(request)
            if headers:
                try:
                    response = requests.delete(
                        f"{settings.GATEWAY_URL}/api/catalog/products/{product_id}/",
                        headers=headers,
                        timeout=5,
                    )
                    if response.status_code == 204:
                        query = urlencode({"msg": "Đã xóa sản phẩm"})
                        return redirect(f"{path}?{query}")
                except requests.RequestException:
                    pass

            query = urlencode({"error": "Lỗi khi xóa sản phẩm"})
            return redirect(f"{path}?{query}")

        if action == "add":
            product_data = _build_staff_product_payload(product_type, request)

            headers = _staff_auth_headers(request)
            if headers:
                try:
                    response = requests.post(
                        f"{settings.GATEWAY_URL}/api/catalog/products/",
                        json=product_data,
                        headers=headers,
                        timeout=5,
                    )
                    if response.status_code == 201:
                        query = urlencode({"msg": "Đã thêm sản phẩm thành công"})
                        return redirect(f"{path}?{query}")
                except requests.RequestException:
                    pass

            query = urlencode({"error": "Lỗi khi thêm sản phẩm"})
            return redirect(f"{path}?{query}")

        if action == "update":
            product_id_raw = request.POST.get("product_id", "0")
            try:
                product_id = int(product_id_raw)
            except ValueError:
                product_id = 0

            if product_id <= 0:
                query = urlencode({"error": "ID sản phẩm không hợp lệ"})
                return redirect(f"{path}?{query}")

            update_data = _build_staff_product_payload(product_type, request)

            headers = _staff_auth_headers(request)
            if headers:
                try:
                    response = requests.put(
                        f"{settings.GATEWAY_URL}/api/catalog/products/{product_id}/",
                        json=update_data,
                        headers=headers,
                        timeout=5,
                    )
                    if response.status_code == 200:
                        query = urlencode({"msg": "Đã cập nhật sản phẩm thành công"})
                        return redirect(f"{path}?{query}")
                except requests.RequestException:
                    pass

            query = urlencode({"error": "Lỗi khi cập nhật sản phẩm"})
            return redirect(f"{path}?{query}")

    categories = _fetch_list(f"/api/catalog/categories/?type={product_type}")

    selected_search = request.GET.get("search", "").strip()
    selected_brand = request.GET.get("brand", "").strip()
    selected_category = request.GET.get("category", "").strip()
    selected_price_min = request.GET.get("price_min", "").strip()
    selected_price_max = request.GET.get("price_max", "").strip()
    selected_stock_min = request.GET.get("stock_min", "").strip()
    selected_stock_max = request.GET.get("stock_max", "").strip()
    selected_sort = request.GET.get("sort", "newest").strip() or "newest"

    params = ["page_size=300"]
    params.append(f"type={product_type}")
    if selected_search:
        params.append(f"search={selected_search}")
    if selected_brand:
        params.append(f"brand={selected_brand}")
    if selected_category:
        params.append(f"category_id={selected_category}")
    if selected_price_min:
        params.append(f"price_min={selected_price_min}")
    if selected_price_max:
        params.append(f"price_max={selected_price_max}")

    ordering_map = {
        "newest": "-created_at",
        "oldest": "created_at",
        "price_asc": "price",
        "price_desc": "-price",
        "name_asc": "name",
        "name_desc": "-name",
    }
    ordering = ordering_map.get(selected_sort)
    if ordering:
        params.append(f"ordering={ordering}")

    products = _fetch_list("/api/catalog/products/?" + "&".join(params))
    stock_min = _to_number(selected_stock_min)
    stock_max = _to_number(selected_stock_max)
    products = _apply_staff_stock_filter_and_sort(
        products if isinstance(products, list) else [],
        stock_min,
        stock_max,
        selected_sort,
    )

    msg = request.GET.get("msg", "")
    error = request.GET.get("error", "")
    edit_id_raw = request.GET.get("edit", "")
    try:
        edit_id = int(edit_id_raw) if edit_id_raw else 0
    except ValueError:
        edit_id = 0

    edit_product = None
    if edit_id > 0:
        edit_product = _fetch_detail(f"/api/catalog/products/{edit_id}/")

    context = {
        "product_type": product_type,
        "product_type_vn": cfg["label"],
        "staff_products_path": path,
        "products": products,
        "categories": categories if isinstance(categories, list) else [],
        "edit_product": edit_product if isinstance(edit_product, dict) else None,
        "brands": sorted(
            {p.get("brand") for p in products if isinstance(p, dict) and p.get("brand")}
        ),
        "selected_search": selected_search,
        "selected_brand": selected_brand,
        "selected_category": selected_category,
        "selected_price_min": selected_price_min,
        "selected_price_max": selected_price_max,
        "selected_stock_min": selected_stock_min,
        "selected_stock_max": selected_stock_max,
        "selected_sort": selected_sort,
        "message": msg,
        "error": error,
        "auth_user_name": request.session.get("auth_user_name", ""),
    }
    return render(request, "store/staff/products.html", context)


@_staff_required
def staff_products_tablet_view(request):
    return _staff_products_generic_view(request, "tablet")


@_staff_required
def staff_products_audio_view(request):
    return _staff_products_generic_view(request, "audio")


@_staff_required
def staff_products_wearable_view(request):
    return _staff_products_generic_view(request, "wearable")


@_staff_required
def staff_products_component_view(request):
    return _staff_products_generic_view(request, "component")


@_staff_required
def staff_products_peripheral_view(request):
    return _staff_products_generic_view(request, "peripheral")


@_staff_required
def staff_products_monitor_view(request):
    return _staff_products_generic_view(request, "monitor")


@_staff_required
def staff_products_accessory_view(request):
    return _staff_products_generic_view(request, "accessory")


@_staff_required
def staff_products_charging_view(request):
    return _staff_products_generic_view(request, "charging")


@_staff_required
def staff_products_book_view(request):
    return _staff_products_generic_view(request, "book")
