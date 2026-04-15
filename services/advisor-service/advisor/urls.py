from django.urls import path

from . import views


urlpatterns = [
    path("events/track/", views.track_event, name="track-event"),
    path("events/trending/", views.trending_events, name="trending-events"),
    path("search/suggest/", views.keyword_suggestions, name="keyword-suggestions"),
    path("search/semantic/", views.semantic_product_search, name="semantic-search"),
    path("recommendations/", views.recommendations, name="recommendations"),
    path("chat/", views.chat, name="chat"),
    path("ai/health/", views.ai_health, name="ai-health"),
    path("ai/health/detailed/", views.ai_health_detailed, name="ai-health-detailed"),
    path("ai/metrics/", views.ai_metrics, name="ai-metrics"),
    path("metrics/latest/", views.metrics_latest, name="metrics-latest"),
    path("metrics/timeseries/", views.metrics_timeseries, name="metrics-timeseries"),
]
