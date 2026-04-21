from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok", "service": "review-service"})


def reviews(request):
    if request.method == "GET":
        return JsonResponse({"count": 0, "results": []})
    if request.method == "POST":
        return JsonResponse(
            {
                "id": 1,
                "status": "submitted",
                "message": "Review skeleton created",
            },
            status=201,
        )
    return JsonResponse({"error": "Method not allowed"}, status=405)


def review_status(request, review_id):
    if request.method == "GET":
        return JsonResponse({"id": review_id, "status": "submitted"})
    if request.method == "PATCH":
        return JsonResponse({"id": review_id, "status": "updated"})
    return JsonResponse({"error": "Method not allowed"}, status=405)


urlpatterns = [
    path("health", health_check, name="health-check"),
    path("api/reviews/", reviews, name="reviews"),
    path("api/reviews/<int:review_id>/status/", review_status, name="review-status"),
]
