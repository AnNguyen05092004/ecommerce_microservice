from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import models
from .models import Staff
from .serializers import StaffSerializer, StaffCreateSerializer, StaffUpdateSerializer


def _require_staff_user(request):
    """Allow only authenticated staff/admin users forwarded by gateway."""
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type != "staff":
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return None


def _require_admin_user(request):
    """Allow only admin users for privileged operations."""
    forbidden_response = _require_staff_user(request)
    if forbidden_response:
        return forbidden_response

    role = request.META.get("HTTP_X_USER_ROLE")
    if role != "admin":
        return Response(
            {"error": "Admin permission required"}, status=status.HTTP_403_FORBIDDEN
        )
    return None


class StaffPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@api_view(["GET", "POST"])
def staff_list_create(request):
    """GET: List staff | POST: Create staff (Admin only)"""
    if request.method == "GET":
        forbidden_response = _require_staff_user(request)
        if forbidden_response:
            return forbidden_response

    if request.method == "POST":
        forbidden_response = _require_admin_user(request)
        if forbidden_response:
            return forbidden_response

    if request.method == "GET":
        queryset = Staff.objects.all()

        # Filters
        role = request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() in ("true", "1"))

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(full_name__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(username__icontains=search)
            )

        paginator = StaffPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StaffSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    elif request.method == "POST":
        serializer = StaffCreateSerializer(data=request.data)
        if serializer.is_valid():
            staff = serializer.save()
            return Response(StaffSerializer(staff).data, status=status.HTTP_201_CREATED)
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET", "PUT", "DELETE"])
def staff_detail(request, pk):
    """GET: Detail | PUT: Update | DELETE: Delete"""
    if request.method in ["GET", "PUT"]:
        forbidden_response = _require_staff_user(request)
        if forbidden_response:
            return forbidden_response

    if request.method == "DELETE":
        forbidden_response = _require_admin_user(request)
        if forbidden_response:
            return forbidden_response

    try:
        staff = Staff.objects.get(pk=pk)
    except Staff.DoesNotExist:
        return Response({"error": "Staff not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = StaffSerializer(staff)
        return Response(serializer.data)

    elif request.method == "PUT":
        serializer = StaffUpdateSerializer(staff, data=request.data, partial=True)
        if serializer.is_valid():
            staff = serializer.save()
            return Response(StaffSerializer(staff).data)
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    elif request.method == "DELETE":
        staff.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
