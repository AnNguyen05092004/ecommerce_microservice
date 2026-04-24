from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok", "service": "payment-service"})


def payments(request):
    if request.method == "GET":
        return JsonResponse({"count": 0, "results": []})
    if request.method == "POST":
        return JsonResponse(
            {
                "id": 1,
                "status": "initiated",
                "message": "Payment skeleton created",
            },
            status=201,
        )
    return JsonResponse({"error": "Method not allowed"}, status=405)


def payment_status(request, payment_id):
    if request.method == "GET":
        return JsonResponse({"id": payment_id, "status": "initiated"})
    if request.method == "PATCH":
        return JsonResponse({"id": payment_id, "status": "updated"})
    return JsonResponse({"error": "Method not allowed"}, status=405)


urlpatterns = [
    path("health", health_check, name="health-check"),
    path("api/payments/", payments, name="payments"),
    path(
        "api/payments/<int:payment_id>/status/",
        payment_status,
        name="payment-status",
    ),
]
