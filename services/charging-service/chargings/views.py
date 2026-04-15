from django.db import models as db_models
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Charging
from .serializers import (
    ChargingSerializer,
    ChargingDetailSerializer,
    ChargingCreateSerializer,
)


def _require_staff_user(request):
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type != "staff":
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return None


def _allow_stock_update(request):
    """Allow stock update for staff requests and trusted internal service calls."""
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type == "staff":
        return None

    internal_service = request.META.get("HTTP_X_INTERNAL_SERVICE", "")
    if internal_service == "customer-service":
        return None

    return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)


class ChargingPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(["GET", "POST"])
def charging_list_create(request):
    """GET: List with search/filter | POST: Create (Staff only)"""
    if request.method == "POST":
        forbidden_response = _require_staff_user(request)
        if forbidden_response:
            return forbidden_response

    if request.method == "GET":
        queryset = Charging.objects.select_related("category").all()

        # Search
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                db_models.Q(name__icontains=search)
                | db_models.Q(brand__icontains=search)
            )

        # Filters
        brand = request.query_params.get("brand")
        if brand:
            queryset = queryset.filter(brand__iexact=brand)

        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category_id=category)

        price_min = request.query_params.get("price_min")
        if price_min:
            queryset = queryset.filter(price__gte=price_min)

        price_max = request.query_params.get("price_max")
        if price_max:
            queryset = queryset.filter(price__lte=price_max)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        valid_orderings = [
            "price",
            "-price",
            "name",
            "-name",
            "created_at",
            "-created_at",
        ]
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)

        paginator = ChargingPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(
            ChargingSerializer(page, many=True).data
        )

    elif request.method == "POST":
        serializer = ChargingCreateSerializer(data=request.data)
        if serializer.is_valid():
            charging = serializer.save()
            return Response(
                ChargingDetailSerializer(charging).data, status=status.HTTP_201_CREATED
            )
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET", "PUT", "DELETE"])
def charging_detail(request, pk):
    """GET: Detail with specs | PUT: Update | DELETE: Delete"""
    if request.method in ["PUT", "DELETE"]:
        forbidden_response = _require_staff_user(request)
        if forbidden_response:
            return forbidden_response

    try:
        charging = Charging.objects.select_related("category").get(pk=pk)
    except Charging.DoesNotExist:
        return Response(
            {"error": "Charging not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        return Response(ChargingDetailSerializer(charging).data)

    elif request.method == "PUT":
        serializer = ChargingCreateSerializer(charging, data=request.data, partial=True)
        if serializer.is_valid():
            charging = serializer.save()
            return Response(ChargingDetailSerializer(charging).data)
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    elif request.method == "DELETE":
        charging.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
def update_stock(request, pk):
    """Update stock (Staff / inter-service)"""
    forbidden_response = _allow_stock_update(request)
    if forbidden_response:
        return forbidden_response

    try:
        charging = Charging.objects.get(pk=pk)
    except Charging.DoesNotExist:
        return Response(
            {"error": "Charging not found"}, status=status.HTTP_404_NOT_FOUND
        )

    stock = request.data.get("stock")
    if stock is None or int(stock) < 0:
        return Response(
            {"error": "Stock must be >= 0"}, status=status.HTTP_400_BAD_REQUEST
        )

    charging.stock = int(stock)
    charging.status = "available" if charging.stock > 0 else "unavailable"
    charging.save()

    return Response(ChargingSerializer(charging).data)
