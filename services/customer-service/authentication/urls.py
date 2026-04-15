from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='customer-register'),
    path('login/', views.login, name='customer-login'),
    path('verify/', views.verify_token, name='verify-token'),
]
