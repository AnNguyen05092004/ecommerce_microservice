from django.urls import path
from . import views

urlpatterns = [
    path('', views.charging_list_create, name='charging-list-create'),
    path('<int:pk>/', views.charging_detail, name='charging-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
