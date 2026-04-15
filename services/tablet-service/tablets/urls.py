from django.urls import path
from . import views

urlpatterns = [
    path('', views.tablet_list_create, name='tablet-list-create'),
    path('<int:pk>/', views.tablet_detail, name='tablet-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
