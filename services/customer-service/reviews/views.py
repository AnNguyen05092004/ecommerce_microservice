from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from customer_service.advisor import track_behavior_event
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer
from customers.models import Customer


def _require_customer_user(request):
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type != "customer":
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return None


class ReviewPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


@api_view(["GET", "POST"])
def review_list_create(request):
    """GET: List reviews by product | POST: Create review (Customer only)"""
    if request.method == "GET":
        product_id = request.query_params.get("product_id")
        product_type = request.query_params.get("product_type")

        if not product_id or not product_type:
            return Response(
                {"error": "product_id and product_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Review.objects.filter(
            product_id=product_id, product_type=product_type
        )
        paginator = ReviewPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(ReviewSerializer(page, many=True).data)

    elif request.method == "POST":
        forbidden_response = _require_customer_user(request)
        if forbidden_response:
            return forbidden_response

        customer_id = request.META.get("HTTP_X_USER_ID")
        if not customer_id:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = ReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Check if already reviewed
        if Review.objects.filter(
            customer_id=customer_id,
            product_id=data["product_id"],
            product_type=data["product_type"],
        ).exists():
            return Response(
                {"error": "You already reviewed this product"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get customer name
        customer_name = ""
        try:
            customer = Customer.objects.get(pk=customer_id)
            customer_name = customer.full_name
        except Customer.DoesNotExist:
            pass

        review = Review.objects.create(
            customer_id=customer_id, customer_name=customer_name, **data
        )

        track_behavior_event(
            {
                "user_id": customer_id,
                "session_id": f"customer-{customer_id}",
                "event_type": "review_created",
                "product_type": data["product_type"],
                "product_id": data["product_id"],
                "quantity": 1,
                "language": "vi",
                "metadata": {"rating": data["rating"]},
            }
        )

        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
