from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok", "service": "cart-service"})


def carts(request):
    if request.method == "GET":
        return JsonResponse({"count": 0, "results": []})
    if request.method == "POST":
        return JsonResponse(
            {
                "id": 1,
                "status": "draft",
                "message": "Cart skeleton created",
            },
            status=201,
        )
    return JsonResponse({"error": "Method not allowed"}, status=405)


def cart_status(request, cart_id):
    if request.method == "GET":
        return JsonResponse({"id": cart_id, "status": "draft"})
    if request.method == "PATCH":
        return JsonResponse({"id": cart_id, "status": "updated"})
    return JsonResponse({"error": "Method not allowed"}, status=405)


urlpatterns = [
    path("health", health_check, name="health-check"),
    path("api/carts/", carts, name="carts"),
    path("api/carts/<int:cart_id>/status/", cart_status, name="cart-status"),
]
