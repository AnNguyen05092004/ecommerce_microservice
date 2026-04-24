from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok", "service": "inventory-service"})


def inventory(request):
    if request.method == "GET":
        return JsonResponse({"count": 0, "results": []})
    if request.method == "POST":
        return JsonResponse(
            {
                "id": 1,
                "status": "active",
                "message": "Inventory skeleton created",
            },
            status=201,
        )
    return JsonResponse({"error": "Method not allowed"}, status=405)


def inventory_status(request, inventory_id):
    if request.method == "GET":
        return JsonResponse({"id": inventory_id, "status": "active"})
    if request.method == "PATCH":
        return JsonResponse({"id": inventory_id, "status": "updated"})
    return JsonResponse({"error": "Method not allowed"}, status=405)


urlpatterns = [
    path("health", health_check, name="health-check"),
    path("api/inventory/", inventory, name="inventory"),
    path(
        "api/inventory/<int:inventory_id>/status/",
        inventory_status,
        name="inventory-status",
    ),
]
