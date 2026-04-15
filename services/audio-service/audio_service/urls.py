from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('health', health_check, name='health-check'),
    path('api/audios/', include('audios.urls')),
    path('api/categories/', include('categories.urls')),
]
