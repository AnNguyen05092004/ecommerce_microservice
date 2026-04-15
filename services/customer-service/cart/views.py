import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from customer_service.advisor import track_behavior_event
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, CartItemCreateSerializer


def _require_customer_user(request):
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type != "customer":
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return None


def get_product_info(product_id, product_type):
    """Fetch product info from product services by type."""
    try:
        product_routes = {
            "computer": (settings.COMPUTER_SERVICE_URL, "computers"),
            "mobile": (settings.MOBILE_SERVICE_URL, "mobiles"),
            "clothes": (settings.CLOTHES_SERVICE_URL, "clothes"),
            "tablet": (settings.TABLET_SERVICE_URL, "tablets"),
            "audio": (settings.AUDIO_SERVICE_URL, "audios"),
            "wearable": (settings.WEARABLE_SERVICE_URL, "wearables"),
            "component": (settings.COMPONENT_SERVICE_URL, "components"),
            "peripheral": (settings.PERIPHERAL_SERVICE_URL, "peripherals"),
            "monitor": (settings.MONITOR_SERVICE_URL, "monitors"),
            "accessory": (settings.ACCESSORY_SERVICE_URL, "accessories"),
            "charging": (settings.CHARGING_SERVICE_URL, "chargings"),
            "book": (settings.BOOK_SERVICE_URL, "books"),
        }
        route = product_routes.get(product_type)
        if not route:
            return None
        base_url, endpoint = route
        url = f"{base_url}/api/{endpoint}/{product_id}/"

        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None


def _normalize_price(value):
    """Normalize external price formats to Decimal-compatible string."""
    if value is None:
        return Decimal("0.00")

    text = str(value).strip()
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".,-")
    if not cleaned:
        return Decimal("0.00")

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


@api_view(["GET"])
def get_cart(request):
    """Get or create cart for current customer"""
    forbidden_response = _require_customer_user(request)
    if forbidden_response:
        return forbidden_response

    customer_id = request.META.get("HTTP_X_USER_ID")
    if not customer_id:
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED
        )

    cart, _ = Cart.objects.get_or_create(customer_id=customer_id)
    return Response(CartSerializer(cart).data)


@api_view(["POST"])
def add_to_cart(request):
    """Add product to cart"""
    forbidden_response = _require_customer_user(request)
    if forbidden_response:
        return forbidden_response

    customer_id = request.META.get("HTTP_X_USER_ID")
    if not customer_id:
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED
        )

    serializer = CartItemCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    product_info = get_product_info(data["product_id"], data["product_type"])

    if not product_info:
        return Response(
            {"error": "Product not found"}, status=status.HTTP_400_BAD_REQUEST
        )

    if product_info.get("stock", 0) < data["quantity"]:
        return Response(
            {"error": "Not enough stock"}, status=status.HTTP_400_BAD_REQUEST
        )

    cart, _ = Cart.objects.get_or_create(customer_id=customer_id)

    # Update if exists, create if not
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product_id=data["product_id"],
        product_type=data["product_type"],
        defaults={
            "product_name": product_info.get("name", ""),
            "product_image": product_info.get("image", ""),
            "quantity": data["quantity"],
            "price": product_info.get("price", 0),
        },
    )

    if not created:
        cart_item.quantity += data["quantity"]
        cart_item.price = _normalize_price(product_info.get("price", cart_item.price))
        cart_item.save()
    else:
        cart_item.price = _normalize_price(cart_item.price)
        cart_item.save(update_fields=["price"])

    track_behavior_event(
        {
            "user_id": customer_id,
            "session_id": f"customer-{customer_id}",
            "event_type": "add_to_cart",
            "product_type": data["product_type"],
            "product_id": data["product_id"],
            "quantity": cart_item.quantity,
            "price": str(cart_item.price),
            "language": "vi",
            "metadata": {"created": created},
        }
    )

    return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "DELETE"])
def update_cart_item(request, pk):
    """Update quantity or remove cart item"""
    forbidden_response = _require_customer_user(request)
    if forbidden_response:
        return forbidden_response

    customer_id = request.META.get("HTTP_X_USER_ID")
    if not customer_id:
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        cart_item = CartItem.objects.get(pk=pk, cart__customer_id=customer_id)
    except CartItem.DoesNotExist:
        return Response(
            {"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "PUT":
        quantity = request.data.get("quantity")
        try:
            quantity_value = int(quantity)
        except (TypeError, ValueError):
            quantity_value = 0

        if quantity_value < 1:
            return Response(
                {"error": "Quantity must be >= 1"}, status=status.HTTP_400_BAD_REQUEST
            )
        cart_item.quantity = quantity_value
        cart_item.save()
        track_behavior_event(
            {
                "user_id": customer_id,
                "session_id": f"customer-{customer_id}",
                "event_type": "update_cart",
                "product_type": cart_item.product_type,
                "product_id": cart_item.product_id,
                "quantity": cart_item.quantity,
                "price": str(cart_item.price),
                "language": "vi",
            }
        )
        return Response(CartItemSerializer(cart_item).data)

    elif request.method == "DELETE":
        track_behavior_event(
            {
                "user_id": customer_id,
                "session_id": f"customer-{customer_id}",
                "event_type": "remove_from_cart",
                "product_type": cart_item.product_type,
                "product_id": cart_item.product_id,
                "quantity": cart_item.quantity,
                "price": str(cart_item.price),
                "language": "vi",
            }
        )
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
