from django.urls import path

from . import views

app_name = "stats"

urlpatterns = [
    path("single-exercise/<content:exercise>/", views.single_exercise, name="single_exercise"),
    path(
        "instance-console/<course:course>/<instance:instance>/",
        views.instance_console,
        name="instance_console",
    ),
    path(
        "generate/<course:course>/<instance:instance>/",
        views.generate_instance_stats,
        name="generate_instance_stats",
    ),
]
