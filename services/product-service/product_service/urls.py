from django.http import JsonResponse
from django.urls import path
from catalog import views


def health_check(request):
    return JsonResponse({"status": "ok", "service": "product-service"})


urlpatterns = [
    path("health", health_check, name="health-check"),
    path(
        "api/categories/", views.categories_list_create, name="categories-list-create"
    ),
    path("api/product-types/", views.product_types, name="product-types"),
    path("api/products/", views.products_list, name="products-list"),
    path(
        "api/products/<int:product_id>/",
        views.product_detail_crud,
        name="products-detail-crud",
    ),
    path(
        "api/products/<int:product_id>/stock/",
        views.product_stock_update,
        name="products-stock-update",
    ),
    path(
        "api/products/<str:product_type>/<int:product_id>/",
        views.product_detail,
        name="product-detail",
    ),
]
