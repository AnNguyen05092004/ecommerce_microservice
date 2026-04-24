import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from customer_service.advisor import track_behavior_event
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderDetailSerializer, OrderCreateSerializer
from cart.models import Cart


def _require_customer_user(request):
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type != "customer":
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return None


def _require_staff_user(request):
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type != "staff":
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return None


class OrderPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class StockUpdateError(Exception):
    """Raised when inter-service stock update fails during checkout."""


def update_product_stock(product_id, product_type, new_stock):
    """Update stock in product service"""
    try:
        if not product_type:
            return False
        url = f"{settings.PRODUCT_SERVICE_URL}/api/products/{product_id}/stock/"

        response = requests.patch(
            url,
            json={"stock": new_stock},
            headers={"X-Internal-Service": "customer-service"},
            timeout=5,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_product_stock(product_id, product_type):
    """Get current stock from product service"""
    try:
        if not product_type:
            return 0
        url = (
            f"{settings.PRODUCT_SERVICE_URL}/api/products/"
            f"{str(product_type).strip().lower()}/{product_id}/"
        )

        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("stock", 0)
        return 0
    except requests.RequestException:
        return 0


@api_view(["GET", "POST"])
def order_list_create(request):
    """GET: List orders | POST: Create order from cart"""
    customer_id = request.META.get("HTTP_X_USER_ID")
    user_type = request.META.get("HTTP_X_USER_TYPE", "customer")

    if request.method == "GET":
        if user_type == "staff":
            # Staff sees all orders
            queryset = Order.objects.all()
            cid = request.query_params.get("customer_id")
            if cid:
                queryset = queryset.filter(customer_id=cid)
        else:
            if not customer_id:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            queryset = Order.objects.filter(customer_id=customer_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = OrderPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(OrderSerializer(page, many=True).data)

    elif request.method == "POST":
        forbidden_response = _require_customer_user(request)
        if forbidden_response:
            return forbidden_response

        if not customer_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get cart items
        try:
            cart = Cart.objects.get(customer_id=customer_id)
            cart_items = cart.items.all()
        except Cart.DoesNotExist:
            return Response(
                {"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not cart_items.exists():
            return Response(
                {"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Verify stock for all items
        track_behavior_event(
            {
                "user_id": customer_id,
                "session_id": f"customer-{customer_id}",
                "event_type": "checkout_start",
                "language": "vi",
                "metadata": {"cart_size": cart_items.count()},
            }
        )

        for item in cart_items:
            current_stock = get_product_stock(item.product_id, item.product_type)
            if current_stock < item.quantity:
                return Response(
                    {
                        "error": f"Not enough stock for {item.product_name}. Available: {current_stock}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        data = serializer.validated_data

        try:
            with transaction.atomic():
                # Create order
                total = sum(item.subtotal for item in cart_items)
                order = Order.objects.create(
                    customer_id=customer_id,
                    total_amount=total,
                    shipping_address=data["shipping_address"],
                    phone=data["phone"],
                    note=data.get("note", ""),
                )

                # Create order items and update stock
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product_id=item.product_id,
                        product_type=item.product_type,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        price=item.price,
                    )
                    # Reduce stock
                    current_stock = get_product_stock(
                        item.product_id, item.product_type
                    )
                    stock_updated = update_product_stock(
                        item.product_id,
                        item.product_type,
                        current_stock - item.quantity,
                    )
                    if not stock_updated:
                        raise StockUpdateError(item.product_name)

                # Clear cart only after all stock updates are successful
                cart_items.delete()
        except StockUpdateError as exc:
            return Response(
                {"error": f"Failed to update stock for {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        track_behavior_event(
            {
                "user_id": customer_id,
                "session_id": f"customer-{customer_id}",
                "event_type": "order_created",
                "price": str(order.total_amount),
                "language": "vi",
                "metadata": {
                    "order_id": order.id,
                    "item_count": order.items.count(),
                    "product_types": [item.product_type for item in order.items.all()],
                },
            }
        )

        return Response(
            OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED
        )


@api_view(["GET"])
def order_detail(request, pk):
    """Get order detail"""
    customer_id = request.META.get("HTTP_X_USER_ID")
    user_type = request.META.get("HTTP_X_USER_TYPE", "customer")

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    # Customer can only see own orders
    if user_type != "staff" and str(order.customer_id) != str(customer_id):
        return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(OrderDetailSerializer(order).data)


@api_view(["PATCH"])
def update_order_status(request, pk):
    """Update order status (Staff only)"""
    forbidden_response = _require_staff_user(request)
    if forbidden_response:
        return forbidden_response

    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get("status")
    valid_statuses = ["confirmed", "shipping", "completed", "cancelled"]
    if new_status not in valid_statuses:
        return Response(
            {"error": f"Status must be one of: {valid_statuses}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order.status = new_status
    order.save()
    return Response(OrderSerializer(order).data)
