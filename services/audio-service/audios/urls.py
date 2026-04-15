from django.urls import path
from . import views

urlpatterns = [
    path('', views.audio_list_create, name='audio-list-create'),
    path('<int:pk>/', views.audio_detail, name='audio-detail'),
    path('<int:pk>/stock/', views.update_stock, name='update-stock'),
]
