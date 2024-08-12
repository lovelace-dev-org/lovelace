from django.urls import path
from . import views

app_name = "api"

urlpatterns = [
    path("users/", views.UserCollection.as_view(), name="users")
]
