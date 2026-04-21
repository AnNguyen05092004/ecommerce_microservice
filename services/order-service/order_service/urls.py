from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok", "service": "order-service"})


def orders(request):
    if request.method == "GET":
        return JsonResponse({"count": 0, "results": []})
    if request.method == "POST":
        return JsonResponse(
            {
                "id": 1,
                "status": "pending",
                "message": "Order skeleton created",
            },
            status=201,
        )
    return JsonResponse({"error": "Method not allowed"}, status=405)


def order_status(request, order_id):
    if request.method == "GET":
        return JsonResponse({"id": order_id, "status": "pending"})
    if request.method == "PATCH":
        return JsonResponse({"id": order_id, "status": "updated"})
    return JsonResponse({"error": "Method not allowed"}, status=405)


urlpatterns = [
    path("health", health_check, name="health-check"),
    path("api/orders/", orders, name="orders"),
    path("api/orders/<int:order_id>/status/", order_status, name="order-status"),
]
