from django.http import HttpResponse, JsonResponse, \
    HttpResponseNotFound, HttpResponseForbidden, HttpResponseRedirect,\
    HttpResponseNotAllowed
from django.urls import reverse
from django.utils.translation import gettext as _
from courses.forms import CalendarConfigForm, CalendarSchedulingForm, MessageForm
from courses.models import *
from utils.access import ensure_staff
from utils.management import CourseContentAdmin
from utils.notify import send_email

@ensure_staff
def calendar_scheduling(request, course, instance, calendar):
    if request.method == "POST":
        form = CalendarSchedulingForm(request.POST)
        print(request.POST["start"])
        if form.is_valid():
            start = form.cleaned_data["start"]
            increment = form.cleaned_data["event_duration"] * 60
            slots = form.cleaned_data["event_slots"]
            for i in range(form.cleaned_data["event_count"]):
                event_start = start + increment * i
                event = CalendarDate(
                    calendar=calendar,
                    start_time=event_start,
                    end_time=event_start + increment,
                    reservable_slots=slots
                )
                for lang_code, lang_name in settings.LANGUAGES:
                    field = "event_name_" + lang_code
                    setattr(event, field, form.cleaned_data[field])
                
                event.save()
            return JsonResponse({"status": "ok"})
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        form = CalendarSchedulingForm()
        t = loader.get_template("courses/base-edit-form.html")
        c = {
            "form_object": form,
            "submit_url": request.path,
            "html_class": "calendar-form staff-only"
        }
        return HttpResponse(t.render(c, request))

@ensure_staff
def adjust_slots(request, course, instance, event, action):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    amount = [-1, 1][action == "incr"]
    event.reservable_slots += amount
    if event.reservable_slots <= 0:
        event.delete()
        deleted = True
    else:
        event.save()
        deleted = False

    reservations = CalendarReservation.objects.filter(calendar_date=event).count()
    return JsonResponse({
        "status": "ok",
        "content": "{} / {}".format(reservations, event.reservable_slots),
        "deleted": deleted
    })
        
@ensure_staff
def calendar_config(request, course, instance, calendar):
    content_access = CourseContentAdmin.content_access_list(request, ContentPage)
    available_content = content_access.defer("content").all()
    
    if request.method == "POST":
        form = CalendarConfigForm(request.POST, available_content=available_content)
        if form.is_valid():
            try:
                content = ContentPage.objects.get(id=form.cleaned_data["related_content"])
            except ContentPage.DoesNotExist:
                content = None            
            calendar.related_content = content
            calendar.allow_multiple = form.cleaned_data["allow_multiple"]
            calendar.save()
            return JsonResponse({"status": "ok"})
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        form = CalendarConfigForm(
            instance=calendar,
            available_content=available_content,
            initial={
                "related_content": calendar.related_content and calendar.related_content.id
            }
        )
        t = loader.get_template("courses/base-edit-form.html")
        c = {
            "form_object": form,
            "submit_url": request.path,
            "html_class": "calendar-form staff-only"
        }
        return HttpResponse(t.render(c, request))
    
    
@ensure_staff
def message_reservers(request, course, instance, calendar):
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            cal_dates = calendar.calendardate_set.get_queryset()
            reservers = set()
            for cal_date in cal_dates:
                for reservation in cal_date.calendarreservation_set.get_queryset().select_related(
                    "user"
                ):
                    reservers.add(reservation.user)
            send_email(
                reservers,
                request.user,
                form.cleaned_data["title"],
                form.cleaned_data["content"],
            )
            return JsonResponse({"status": "ok"})            
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        form_object = MessageForm()
        form_t = loader.get_template("courses/base-edit-form.html")
        form_c = {
            "form_object": form_object,
            "submit_url": request.path,
            "html_class": "message-form",
            "disclaimer": _("Send message to all reservers")
        }
        t = loader.get_template("courses/direct-message-panel.html")
        c = {
            "form": form_t.render(form_c, request)
        }
        return HttpResponse(t.render(c, request))
        
    
    
# TODO: calendars should be tied to instances
def calendar_reservation(request, calendar, event):
    if not request.user.is_authenticated:
        return HttpResponseNotFound()
    if not request.method == "POST":
        return HttpResponseNotFound()
    form = request.POST

    reservations = CalendarReservation.objects.filter(calendar_date=event)
    reserved_slots = reservations.count()
    total_slots = event.reservable_slots
    if "reserve" in form.keys() and int(form["reserve"]) == 1:
        # TODO: How to make this atomic? Use with transaction.atomic
        if reserved_slots >= total_slots:
            return JsonResponse(
                {
                    "msg": _("This event is already full.")
                }, 
                status=400
            )
        user_reservations = reservations.filter(user=request.user)
        if user_reservations.count() >= 1:
            return JsonResponse(
                {
                    "msg": _("You have already reserved a slot in this event.")
                },
                status=400
            )
        new_reservation = CalendarReservation(calendar_date=event, user=request.user)
        new_reservation.save()
        # TODO: Check that we didn't overfill the event
        return JsonResponse({
            "msg": _("Slot reserved!"),
            "slots": "{} / {}".format(reserved_slots + 1, total_slots),
            "full": reserved_slots + 1 >= total_slots,
            "can_reserve": calendar.allow_multiple
        })
    elif "reserve" in form.keys() and int(form["reserve"]) == 0:
        user_reservations = CalendarReservation.objects.filter(
            calendar_date=event, user=request.user
        )
        if user_reservations.count() >= 1:
            user_reservations.delete()
            return JsonResponse({
                "msg": _("Reservation cancelled."),
                "slots": "{} / {}".format(reserved_slots - 1, total_slots),
                "full": reserved_slots - 1 >= total_slots,
                "can_reserve": True
            })
        else:
            return HttpResponse({
                "msg": _("Reservation already cancelled."),
                "slots": "{} / {}".format(reserved_slots, total_slots),
                "full": reserved_slots >= total_slots,
                "can_reserve": True
            })
    else:
        return HttpResponseForbidden()

