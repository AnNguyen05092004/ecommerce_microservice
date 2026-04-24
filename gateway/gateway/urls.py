from django.urls import path, re_path
from django.http import JsonResponse
from proxy import views


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health_check, name="health-check"),
    # Bounded-context facades (DDD migration path)
    re_path(r"^api/identity/(?P<path>.*)$", views.proxy_identity_context),
    re_path(r"^api/catalog/(?P<path>.*)$", views.proxy_catalog_context),
    re_path(r"^api/inventory/(?P<path>.*)$", views.proxy_inventory_context),
    re_path(r"^api/cart/(?P<path>.*)$", views.proxy_cart_context),
    re_path(r"^api/orders/(?P<path>.*)$", views.proxy_orders_context),
    re_path(r"^api/payments/(?P<path>.*)$", views.proxy_payments_context),
    re_path(r"^api/reviews/(?P<path>.*)$", views.proxy_reviews_context),
    re_path(r"^api/advisor/(?P<path>.*)$", views.proxy_advisor_context),
    # Legacy and dynamic service routes
    re_path(r"^api/(?P<service_name>[a-z0-9-]+)/(?P<path>.*)$", views.proxy_service),
]
