from django.shortcuts import render
from utils.access import ensure_enrolled, ensure_staff

# Create your views here.

@ensure_enrolled
def request_credits(request, instance):
    pass


@ensure_staff
def view_tickets(request, instance):
    pass
