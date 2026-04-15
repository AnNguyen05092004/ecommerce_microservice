from django.urls import path
from . import views
urlpatterns = [
    path('', views.category_list_create, name='category-list-create'),
    path('<int:pk>/', views.category_detail, name='category-detail'),
]
