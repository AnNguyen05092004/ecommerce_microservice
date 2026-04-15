from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_cart, name='get-cart'),
    path('items/', views.add_to_cart, name='add-to-cart'),
    path('items/<int:pk>/', views.update_cart_item, name='update-cart-item'),
]
