from django.urls import path
from . import views
urlpatterns = [
    path('', views.mobile_list_create, name='mobile-list-create'),
    path('<int:pk>/', views.mobile_detail, name='mobile-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
