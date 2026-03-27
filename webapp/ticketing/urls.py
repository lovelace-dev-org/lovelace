from django.urls import path
from . import views

app_name = "ticketing"

urlpatterns = [

    # User views
    path(
        "<instance:instance>/request_credits",
        views.request_credits,
        name="request_credits",
    ),
    path(
        "<instance:instance>/view_tickets",
        views.view_tickets,
        name="view_tickets",
    ),
]

