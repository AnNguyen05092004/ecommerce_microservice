from django.urls import path
from . import views

urlpatterns = [
    path('', views.accessory_list_create, name='accessory-list-create'),
    path('<int:pk>/', views.accessory_detail, name='accessory-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
