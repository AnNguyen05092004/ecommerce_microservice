from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list_create, name='order-list-create'),
    path('<int:pk>/', views.order_detail, name='order-detail'),
    path('<int:pk>/status/', views.update_order_status, name='update-order-status'),
]
