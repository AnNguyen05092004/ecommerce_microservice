from django.urls import path
from . import views

urlpatterns = [
    path('', views.staff_list_create, name='staff-list-create'),
    path('<int:pk>/', views.staff_detail, name='staff-detail'),
]
