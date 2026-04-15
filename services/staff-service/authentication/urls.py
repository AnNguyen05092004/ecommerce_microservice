from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='staff-login'),
    path('verify/', views.verify_token, name='verify-token'),
]
