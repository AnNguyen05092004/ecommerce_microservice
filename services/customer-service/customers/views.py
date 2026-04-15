from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import models as db_models
from .models import Customer
from .serializers import CustomerSerializer, CustomerUpdateSerializer


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


class CustomerPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(["GET", "PUT"])
def my_profile(request):
    """GET/PUT customer's own profile — requires customer_id in header (set by gateway)"""
    forbidden_response = _require_customer_user(request)
    if forbidden_response:
        return forbidden_response

    customer_id = request.META.get("HTTP_X_USER_ID")
    if not customer_id:
        return Response(
            {"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        return Response(CustomerSerializer(customer).data)

    elif request.method == "PUT":
        serializer = CustomerUpdateSerializer(customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CustomerSerializer(customer).data)
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def customer_list(request):
    """List customers (Staff only)"""
    forbidden_response = _require_staff_user(request)
    if forbidden_response:
        return forbidden_response

    queryset = Customer.objects.all()

    search = request.query_params.get("search")
    if search:
        queryset = queryset.filter(
            db_models.Q(full_name__icontains=search)
            | db_models.Q(email__icontains=search)
            | db_models.Q(phone__icontains=search)
        )

    paginator = CustomerPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response(CustomerSerializer(page, many=True).data)


@api_view(["GET"])
def customer_detail(request, pk):
    """Get customer detail (Staff only)"""
    forbidden_response = _require_staff_user(request)
    if forbidden_response:
        return forbidden_response

    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
        )

    return Response(CustomerSerializer(customer).data)
