from django.urls import path
from . import views

urlpatterns = [
    path('', views.monitor_list_create, name='monitor-list-create'),
    path('<int:pk>/', views.monitor_detail, name='monitor-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
