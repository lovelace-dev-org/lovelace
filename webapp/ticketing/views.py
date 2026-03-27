from django.shortcuts import render
from utils.access import ensure_enrolled, ensure_staff
from ticketing.forms import TicketForm

# Create your views here.

@ensure_enrolled
def request_credits(request, instance):
    if request.method == "POST":
        form = TicketForm(request.POST)

    t = loader.get_template("courses/base-edit-form.html")
    form = TicketForm(initial={

    })



@ensure_staff
def view_tickets(request, instance):
    pass
