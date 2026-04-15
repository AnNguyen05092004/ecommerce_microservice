"""customer_service URL Configuration"""
from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('health', health_check, name='health-check'),
    path('api/auth/', include('authentication.urls')),
    path('api/customers/', include('customers.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/reviews/', include('reviews.urls')),
]
