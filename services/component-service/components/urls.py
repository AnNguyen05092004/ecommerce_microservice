from django.urls import path
from . import views

urlpatterns = [
    path('', views.component_list_create, name='component-list-create'),
    path('<int:pk>/', views.component_detail, name='component-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
