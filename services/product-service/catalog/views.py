import json

from django.http import HttpResponse, JsonResponse

from catalog.models import Category, Product


PRODUCT_TYPES = {
    "computer": {"resource": "products", "label": "Laptop"},
    "mobile": {"resource": "products", "label": "Dien thoai"},
    "clothes": {"resource": "products", "label": "Quan ao"},
    "tablet": {"resource": "products", "label": "Tablet"},
    "audio": {"resource": "products", "label": "Audio"},
    "wearable": {"resource": "products", "label": "Wearable"},
    "component": {"resource": "products", "label": "Linh kien"},
    "peripheral": {"resource": "products", "label": "Phu kien PC"},
    "monitor": {"resource": "products", "label": "Man hinh"},
    "accessory": {"resource": "products", "label": "Phu kien dien thoai"},
    "charging": {"resource": "products", "label": "Sac va pin"},
    "book": {"resource": "products", "label": "Sach"},
}


def _to_number(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize(item, product_type):
    category = item.category
    return {
        "id": item.id,
        "product_type": product_type,
        "name": item.name,
        "brand": item.brand,
        "price": float(item.price),
        "stock": item.stock,
        "image": item.image,
        "description": item.description,
        "specs": item.specs or {},
        "status": item.status,
        "category": (
            {"id": category.id, "name": category.name}
            if category
            else {"id": None, "name": ""}
        ),
        "created_at": item.created_at.isoformat() if item.created_at else "",
    }


def _apply_filters(items, search, brand, category, price_min, price_max):
    result = []
    search_text = (search or "").strip().lower()
    brand_text = (brand or "").strip().lower()
    category_text = (category or "").strip().lower()

    for item in items:
        if search_text:
            haystack = " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("brand") or ""),
                    str((item.get("category") or {}).get("name") or ""),
                ]
            ).lower()
            if search_text not in haystack:
                continue

        if brand_text and (item.get("brand") or "").strip().lower() != brand_text:
            continue

        if category_text:
            cat_name = (
                str((item.get("category") or {}).get("name") or "").strip().lower()
            )
            if category_text not in cat_name:
                continue

        price = _to_number(item.get("price"))
        if price_min is not None and (price is None or price < price_min):
            continue
        if price_max is not None and (price is None or price > price_max):
            continue

        result.append(item)

    return result


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _serialize_category(item):
    return {
        "id": item.id,
        "name": item.name,
    }


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_decimal_or_none(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def categories_list_create(request):
    if request.method == "GET":
        selected_type = (request.GET.get("type") or "").strip().lower()
        queryset = Category.objects.all()
        if selected_type in PRODUCT_TYPES:
            queryset = queryset.filter(products__product_type=selected_type).distinct()
        payload = [_serialize_category(item) for item in queryset]
        return JsonResponse(payload, safe=False)

    if request.method == "POST":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        name = str(body.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "name is required"}, status=400)

        category, created = Category.objects.get_or_create(name=name)
        return JsonResponse(
            _serialize_category(category), status=201 if created else 200
        )

    return JsonResponse({"error": "Method not allowed"}, status=405)


def product_types(request):
    payload = [
        {"type": key, "resource": cfg["resource"], "label": cfg["label"]}
        for key, cfg in PRODUCT_TYPES.items()
    ]
    return JsonResponse({"count": len(payload), "results": payload})


def products_list(request):
    if request.method == "POST":
        body = _json_body(request)
        if body is None:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        product_type = str(body.get("product_type") or "").strip().lower()
        if product_type not in PRODUCT_TYPES:
            return JsonResponse({"error": "product_type is invalid"}, status=400)

        name = str(body.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "name is required"}, status=400)

        price_value = _to_decimal_or_none(body.get("price"))
        if price_value is None:
            return JsonResponse({"error": "price is required"}, status=400)

        category = None
        category_id = _to_int(body.get("category_id"), 0)
        if category_id > 0:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return JsonResponse({"error": "category_id not found"}, status=400)

        product = Product.objects.create(
            product_type=product_type,
            name=name,
            brand=str(body.get("brand") or "").strip(),
            price=price_value,
            stock=max(_to_int(body.get("stock"), 0), 0),
            image=str(body.get("image") or "").strip(),
            description=str(body.get("description") or "").strip(),
            specs=body.get("specs") if isinstance(body.get("specs"), dict) else {},
            status=str(body.get("status") or "available").strip() or "available",
            category=category,
        )
        return JsonResponse(_normalize(product, product.product_type), status=201)

    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    selected_type = (request.GET.get("type") or "all").strip().lower()
    category_id = _to_int(request.GET.get("category_id"), 0)
    search = request.GET.get("search", "")
    brand = request.GET.get("brand", "")
    category = request.GET.get("category", "")
    price_min = _to_number(request.GET.get("price_min"))
    price_max = _to_number(request.GET.get("price_max"))
    ordering = (request.GET.get("ordering") or "-created_at").strip()

    try:
        page = max(int(request.GET.get("page", "1")), 1)
    except ValueError:
        page = 1
    try:
        page_size = max(min(int(request.GET.get("page_size", "24")), 96), 1)
    except ValueError:
        page_size = 24

    queryset = Product.objects.select_related("category")
    if selected_type in PRODUCT_TYPES:
        queryset = queryset.filter(product_type=selected_type)
    if category_id > 0:
        queryset = queryset.filter(category_id=category_id)

    rows = [_normalize(item, item.product_type) for item in queryset]

    rows = _apply_filters(rows, search, brand, category, price_min, price_max)

    reverse = ordering.startswith("-")
    key = ordering.lstrip("-")
    if key in ("price", "stock"):
        rows = sorted(rows, key=lambda x: _to_number(x.get(key)) or 0, reverse=reverse)
    elif key in ("name", "created_at"):
        rows = sorted(
            rows, key=lambda x: str(x.get(key) or "").lower(), reverse=reverse
        )

    count = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return JsonResponse(
        {
            "count": count,
            "next": page + 1 if end < count else None,
            "previous": page - 1 if page > 1 else None,
            "results": page_rows,
        }
    )


def product_detail(request, product_type, product_id):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    ptype = (product_type or "").strip().lower()
    if ptype not in PRODUCT_TYPES:
        return JsonResponse({"error": "Unsupported product_type"}, status=400)

    try:
        item = Product.objects.select_related("category").get(
            product_type=ptype,
            id=product_id,
        )
        return JsonResponse(_normalize(item, ptype))
    except Product.DoesNotExist:
        pass

    return JsonResponse({"error": "Product not found"}, status=404)


def product_detail_crud(request, product_id):
    try:
        item = Product.objects.select_related("category").get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(_normalize(item, item.product_type))

    if request.method == "DELETE":
        item.delete()
        return HttpResponse(status=204)

    if request.method not in ("PUT", "PATCH"):
        return JsonResponse({"error": "Method not allowed"}, status=405)

    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if "product_type" in body:
        next_type = str(body.get("product_type") or "").strip().lower()
        if next_type not in PRODUCT_TYPES:
            return JsonResponse({"error": "product_type is invalid"}, status=400)
        item.product_type = next_type

    if "name" in body:
        name = str(body.get("name") or "").strip()
        if not name:
            return JsonResponse({"error": "name is required"}, status=400)
        item.name = name
    if "brand" in body:
        item.brand = str(body.get("brand") or "").strip()
    if "price" in body:
        price_value = _to_decimal_or_none(body.get("price"))
        if price_value is None:
            return JsonResponse({"error": "price is invalid"}, status=400)
        item.price = price_value
    if "stock" in body:
        item.stock = max(_to_int(body.get("stock"), item.stock), 0)
    if "image" in body:
        item.image = str(body.get("image") or "").strip()
    if "description" in body:
        item.description = str(body.get("description") or "").strip()
    if "status" in body:
        item.status = str(body.get("status") or "").strip() or item.status
    if "specs" in body and isinstance(body.get("specs"), dict):
        item.specs = body.get("specs")
    if "category_id" in body:
        category_id = _to_int(body.get("category_id"), 0)
        if category_id <= 0:
            item.category = None
        else:
            try:
                item.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return JsonResponse({"error": "category_id not found"}, status=400)

    item.save()
    return JsonResponse(_normalize(item, item.product_type))


def product_stock_update(request, product_id):
    if request.method not in ("PATCH", "PUT"):
        return JsonResponse({"error": "Method not allowed"}, status=405)

    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    stock = _to_int(body.get("stock"), -1)
    if stock < 0:
        return JsonResponse({"error": "stock must be >= 0"}, status=400)

    try:
        item = Product.objects.select_related("category").get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    item.stock = stock
    item.save(update_fields=["stock", "updated_at"])
    return JsonResponse(_normalize(item, item.product_type))
