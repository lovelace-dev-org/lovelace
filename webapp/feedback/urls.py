from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path(
        "statistics/<instance:instance>/<content:content>/",
        views.content_feedback_stats,
        name="statistics",
    ),
    path(
        "<instance:instance>/<content:content>/<feedback:question>/receive/",
        views.receive,
        name="receive",
    ),
]
