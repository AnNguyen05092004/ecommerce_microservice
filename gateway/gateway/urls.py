from django.urls import path, re_path
from django.http import JsonResponse
from proxy import views


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health", health_check, name="health-check"),
    # Staff Service routes
    re_path(r"^api/staff-service/(?P<path>.*)$", views.proxy_staff_service),
    # Customer Service routes
    re_path(r"^api/customer-service/(?P<path>.*)$", views.proxy_customer_service),
    # Computer Service routes
    re_path(r"^api/computer-service/(?P<path>.*)$", views.proxy_computer_service),
    # Mobile Service routes
    re_path(r"^api/mobile-service/(?P<path>.*)$", views.proxy_mobile_service),
    # Clothes Service routes
    re_path(r"^api/clothes-service/(?P<path>.*)$", views.proxy_clothes_service),
    # Tablet Service routes
    re_path(r"^api/tablet-service/(?P<path>.*)$", views.proxy_tablet_service),
    # Audio Service routes
    re_path(r"^api/audio-service/(?P<path>.*)$", views.proxy_audio_service),
    # Wearable Service routes
    re_path(r"^api/wearable-service/(?P<path>.*)$", views.proxy_wearable_service),
    # Component Service routes
    re_path(r"^api/component-service/(?P<path>.*)$", views.proxy_component_service),
    # Peripheral Service routes
    re_path(r"^api/peripheral-service/(?P<path>.*)$", views.proxy_peripheral_service),
    # Monitor Service routes
    re_path(r"^api/monitor-service/(?P<path>.*)$", views.proxy_monitor_service),
    # Accessory Service routes
    re_path(r"^api/accessory-service/(?P<path>.*)$", views.proxy_accessory_service),
    # Charging Service routes
    re_path(r"^api/charging-service/(?P<path>.*)$", views.proxy_charging_service),
    # Book Service routes
    re_path(r"^api/book-service/(?P<path>.*)$", views.proxy_book_service),
    # Advisor Service routes
    re_path(r"^api/advisor-service/(?P<path>.*)$", views.proxy_advisor_service),
]
