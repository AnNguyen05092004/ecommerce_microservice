from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import AudioCategory
from .serializers import CategorySerializer, CategoryCreateSerializer


def _require_staff_user(request):
    user_type = request.META.get("HTTP_X_USER_TYPE")
    if user_type != "staff":
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(["GET", "POST"])
def category_list_create(request):
    if request.method == "GET":
        categories = AudioCategory.objects.all()
        return Response(CategorySerializer(categories, many=True).data)

    elif request.method == "POST":
        forbidden_response = _require_staff_user(request)
        if forbidden_response:
            return forbidden_response

        serializer = CategoryCreateSerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            return Response(
                CategorySerializer(category).data, status=status.HTTP_201_CREATED
            )
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET", "PUT", "DELETE"])
def category_detail(request, pk):
    try:
        category = AudioCategory.objects.get(pk=pk)
    except AudioCategory.DoesNotExist:
        return Response(
            {"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        return Response(CategorySerializer(category).data)
    elif request.method == "PUT":
        forbidden_response = _require_staff_user(request)
        if forbidden_response:
            return forbidden_response

        serializer = CategoryCreateSerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CategorySerializer(category).data)
        return Response(
            {"error": "Validation failed", "detail": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    elif request.method == "DELETE":
        forbidden_response = _require_staff_user(request)
        if forbidden_response:
            return forbidden_response

        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
