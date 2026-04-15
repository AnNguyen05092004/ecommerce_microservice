from django.urls import path
from . import views

urlpatterns = [
    path('', views.book_list_create, name='book-list-create'),
    path('<int:pk>/', views.book_detail, name='book-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
