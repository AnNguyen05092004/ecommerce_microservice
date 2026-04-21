from django.http import JsonResponse
from django.urls import path

from store.views import (
    advisor_chat_view,
    advisor_event_view,
    advisor_keyword_suggest_view,
    advisor_semantic_search_view,
    cart_view,
    customer_orders_view,
    customer_login_view,
    home_view,
    logout_view,
    product_detail_view,
    products_view,
    staff_login_view,
    staff_dashboard_view,
    staff_products_computer_view,
    staff_products_mobile_view,
    staff_products_clothes_view,
    staff_products_tablet_view,
    staff_products_audio_view,
    staff_products_wearable_view,
    staff_products_component_view,
    staff_products_peripheral_view,
    staff_products_monitor_view,
    staff_products_accessory_view,
    staff_products_charging_view,
    staff_products_book_view,
    staff_orders_view,
    staff_customers_view,
    staff_ai_metrics_view,
    staff_ai_report_view,
)


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", home_view, name="home"),
    path("advisor/chat", advisor_chat_view, name="advisor-chat"),
    path("advisor/event", advisor_event_view, name="advisor-event"),
    path(
        "advisor/keyword-suggest",
        advisor_keyword_suggest_view,
        name="advisor-keyword-suggest",
    ),
    path(
        "advisor/semantic-search",
        advisor_semantic_search_view,
        name="advisor-semantic-search",
    ),
    path("cart", cart_view, name="cart"),
    path("my-orders", customer_orders_view, name="my-orders"),
    path("products", products_view, name="products"),
    path(
        "products/<str:product_type>/<int:product_id>",
        product_detail_view,
        name="product-detail",
    ),
    path("login/customer", customer_login_view, name="customer-login"),
    path("login/staff", staff_login_view, name="staff-login"),
    path("logout", logout_view, name="logout"),
    # Staff routes
    path("staff/dashboard", staff_dashboard_view, name="staff-dashboard"),
    path(
        "staff/products/computer",
        staff_products_computer_view,
        name="staff-products-computer",
    ),
    path(
        "staff/products/mobile",
        staff_products_mobile_view,
        name="staff-products-mobile",
    ),
    path(
        "staff/products/clothes",
        staff_products_clothes_view,
        name="staff-products-clothes",
    ),
    path(
        "staff/products/tablet",
        staff_products_tablet_view,
        name="staff-products-tablet",
    ),
    path(
        "staff/products/audio",
        staff_products_audio_view,
        name="staff-products-audio",
    ),
    path(
        "staff/products/wearable",
        staff_products_wearable_view,
        name="staff-products-wearable",
    ),
    path(
        "staff/products/component",
        staff_products_component_view,
        name="staff-products-component",
    ),
    path(
        "staff/products/peripheral",
        staff_products_peripheral_view,
        name="staff-products-peripheral",
    ),
    path(
        "staff/products/monitor",
        staff_products_monitor_view,
        name="staff-products-monitor",
    ),
    path(
        "staff/products/accessory",
        staff_products_accessory_view,
        name="staff-products-accessory",
    ),
    path(
        "staff/products/charging",
        staff_products_charging_view,
        name="staff-products-charging",
    ),
    path(
        "staff/products/book",
        staff_products_book_view,
        name="staff-products-book",
    ),
    path("staff/orders", staff_orders_view, name="staff-orders"),
    path("staff/customers", staff_customers_view, name="staff-customers"),
    path("admin/ai-metrics", staff_ai_metrics_view, name="staff-ai-metrics"),
    path(
        "admin/ai-reports/<str:report_key>",
        staff_ai_report_view,
        name="staff-ai-report",
    ),
    path("health", health_check, name="health-check"),
]
