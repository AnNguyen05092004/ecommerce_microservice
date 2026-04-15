from django.urls import path
from . import views

urlpatterns = [
    path('', views.computer_list_create, name='computer-list-create'),
    path('<int:pk>/', views.computer_detail, name='computer-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
