from django.urls import path
from . import views

urlpatterns = [
    path('', views.clothes_list_create, name='clothes-list-create'),
    path('<int:pk>/', views.clothes_detail, name='clothes-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
