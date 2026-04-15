"""staff_service URL Configuration"""
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path('health', health_check, name='health-check'),
    path('api/auth/', include('authentication.urls')),
    path('api/staff/', include('staff.urls')),
]
