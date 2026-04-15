from django.urls import path
from . import views

urlpatterns = [
    path('', views.wearable_list_create, name='wearable-list-create'),
    path('<int:pk>/', views.wearable_detail, name='wearable-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
