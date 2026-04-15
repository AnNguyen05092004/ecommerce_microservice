from django.urls import path
from . import views

urlpatterns = [
    path('', views.peripheral_list_create, name='peripheral-list-create'),
    path('<int:pk>/', views.peripheral_detail, name='peripheral-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
