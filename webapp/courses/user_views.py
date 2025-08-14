import secrets
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseNotFound,
    HttpResponseForbidden,
    HttpResponseRedirect,
    HttpResponseNotAllowed,
)
from django.template import loader
from django.conf import settings
from django.core.cache import caches
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib import auth, messages
from django.shortcuts import redirect
from django.db.utils import IntegrityError

from allauth.account.forms import LoginForm

from courses.models import (
    GroupInvitation,
    StudentGroup,
    UserCheckboxExerciseAnswer,
    UserFileUploadExerciseAnswer,
    UserMultipleChoiceExerciseAnswer,
    UserProfile,
    UserRepeatedTemplateExerciseAnswer,
    UserTextfieldExerciseAnswer,
)
from courses.forms import GroupConfigForm, GroupInviteForm, UserForm, UserProfileForm
from courses.views import system_messages
from utils.access import (
    ensure_enrolled_or_staff,
    is_course_staff,
)
from utils.users import get_group_members

try:
    from shibboleth.app_settings import LOGOUT_URL, LOGOUT_REDIRECT_URL
except ImportError:
    # shibboleth not installed
    # these are not needed
    LOGOUT_URL = ""
    LOGOUT_REDIRECT_URL = ""


# LOGIN
# |
# v

@system_messages
def login(request):
    # template based on allauth login page
    t = loader.get_template("courses/login.html")
    c = {"login_form": LoginForm(), "signup_url": reverse("account_signup")}

    if "shibboleth" in settings.INSTALLED_APPS:
        c["shibboleth_login"] = reverse("shibboleth:login")
    else:
        c["shibboleth_login"] = False

    return HttpResponse(t.render(c, request))


@system_messages
def logout(request):
    # template based on allauth logout page
    t = loader.get_template("courses/logout.html")

    if request.method == "POST":
        # handle shibboleth logout
        # from shibboleth login view

        auth.logout(request)
        target = LOGOUT_REDIRECT_URL
        logout = LOGOUT_URL % target
        return redirect(logout)

    if request.session.get("shib", None):
        c = {"logout_url": reverse("courses:logout")}
    else:
        c = {"logout_url": reverse("account_logout")}
    return HttpResponse(t.render(c, request))

# ^
# |
# LOGIN
# PROFILE
# |
# v


def user_profile(request):
    """
    Allow the user to change information in their profile.
    """
    if not request.user.is_authenticated:
        return HttpResponseNotFound()

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save()
            messages.add_message(request, messages.INFO, _("Profile saved."))
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.userprofile)

    t = loader.get_template("courses/userprofile.html")
    c = {
        "user_form": user_form,
        "profile_form": profile_form,
        "user": request.user,
        "submit_url": request.path,
        "data_retention_period": settings.DATA_RETENTION_PERIOD,
    }
    response = HttpResponse(t.render(c, request))
    return response


def user(request, user):
    """
    Shows user information to the requesting user. The amount of information
    depends on who the requesting user is.
    """
    requester = request.user

    if not (requester.is_authenticated and requester.is_active):
        return HttpResponseForbidden(_("Please log in to view your information."))
    if not requester.is_staff and requester != user:
        return HttpResponseForbidden(_("You are only allowed to view your own information."))

    checkboxexercise_answers = UserCheckboxExerciseAnswer.objects.filter(user=user)
    multiplechoiceexercise_answers = UserMultipleChoiceExerciseAnswer.objects.filter(user=user)
    textfieldexercise_answers = UserTextfieldExerciseAnswer.objects.filter(user=user)
    fileexercise_answers = UserFileUploadExerciseAnswer.objects.filter(user=user)
    repeatedtemplateexercise_answers = UserRepeatedTemplateExerciseAnswer.objects.filter(user=user)

    t = loader.get_template("courses/userinfo.html")
    c = {
        "checkboxexercise_answers": checkboxexercise_answers,
        "multiplechoiceexercise_answers": multiplechoiceexercise_answers,
        "textfieldexercise_answers": textfieldexercise_answers,
        "fileexercise_answers": fileexercise_answers,
        "repeatedtemplateexercise_answers": repeatedtemplateexercise_answers,
    }
    return HttpResponse(t.render(c, request))

# ^
# |
# PROFILE
# GROUP
# |
# v

@ensure_enrolled_or_staff
def group_info(request, course, instance):
    if instance.max_group_size is None:
        return HttpResponseNotAllowed(_("This course instance doesn't allow groups"))

    user_groups = request.user.studentgroup_set.get_queryset()
    try:
        group = user_groups.get(instance=instance)
        members = group.members.count()
        invites = GroupInvitation.objects.filter(group=group)
        slots = instance.max_group_size - members - invites.count()
        is_supervisor = request.user in (group.supervisor, course.main_responsible)
    except StudentGroup.DoesNotExist:
        group = None
        members = 0
        slots = instance.max_group_size
        invites = []
        is_supervisor = request.user == course.main_responsible

    invited_to = GroupInvitation.objects.filter(user=request.user, group__instance=instance)
    if request.method == "POST":
        form = GroupConfigForm(request.POST, instance=group)
        if form.is_valid():
            if group is None:
                group = form.save(commit=False)
                group.instance = instance
                group.save()
                group.members.add(request.user)
            else:
                form.save(commit=True)
            return redirect(request.path)
    else:
        config_form = GroupConfigForm(instance=group)

    form_t = loader.get_template("courses/base-edit-form.html")
    config_c = {
        "form_object": config_form,
        "html_class": "group-form",
        "submit_url": request.path,
    }

    c = {
        "group": group,
        "member_count": members,
        "max_members": instance.max_group_size,
        "config_form": form_t.render(config_c, request),
        "invites": invites,
        "slots": slots,
        "course": course,
        "instance": instance,
        "invited_to": invited_to,
        "is_supervisor": is_supervisor,
        "course_staff": is_course_staff(request.user, instance),
    }

    if slots and group:
        invite_form = GroupInviteForm(slots=slots)
        invite_c = {
            "form_object": invite_form,
            "html_class": "invite-form",
            "disclaimer": _("Write the usernames of users you want to invite"),
            "submit_url": reverse(
                "courses:invite_members",
                kwargs={
                    "course": course,
                    "instance": instance,
                    "group": group,
                },
            ),
        }
        c["invite_form"] = form_t.render(invite_c, request)

    t = loader.get_template("courses/group-info.html")
    return HttpResponse(t.render(c, request))


def invite_members(request, course, instance, group):
    if not group.members.filter(pk=request.user.pk).exists() and request.user != group.supervisor:
        return HttpResponseForbidden(_("Can't invite users to groups you're not a member of"))

    if request.method != "POST":
        return HttpResponseNotFound()

    members = group.members.count()
    invites = GroupInvitation.objects.filter(group=group)
    slots = instance.max_group_size - members - invites.count()
    form = GroupInviteForm(request.POST, slots=slots)
    if not form.is_valid(for_instance=instance):
        errors = form.errors.as_json()
        return JsonResponse({"errors": errors}, status=400)

    for user in form.invited_users:
        try:
            invite = GroupInvitation(
                group=group,
                user=user,
                sender=request.user,
            )
            invite.save()
        except IntegrityError:
            pass
    return JsonResponse({"status": "ok"})


def accept_invitation(request, course, instance, invite):
    if request.method != "POST":
        return HttpResponseNotFound()

    if invite.user != request.user:
        return HttpResponseNotFound()

    other_group_members = get_group_members(request.user, instance)
    if other_group_members.count() >= 1:
        return HttpResponseNotAllowed(
            _("Can't accept invitation, already a member of another group")
        )

    StudentGroup.objects.filter(instance=instance, members=request.user).delete()

    invite.group.members.add(request.user)
    GroupInvitation.objects.filter(user=request.user, group__instance=instance).delete()
    return redirect(reverse("courses:group_info", kwargs={"course": course, "instance": instance}))


def cancel_invitation(request, course, instance, group, invite):
    if not group.members.filter(pk=request.user.pk).exists() and request.user != group.supervisor:
        return HttpResponseForbidden(
            _("Can't manage invitations for groups you're not a member of")
        )

    if request.method != "POST":
        return HttpResponseNotFound()

    invite.delete()
    return redirect(reverse("courses:group_info", kwargs={"course": course, "instance": instance}))

# ^
# |
# GROUP
# WS
# |
# v

@ensure_enrolled_or_staff
def get_ws_ticket(request, course, instance, widget_id):
    ticket_key = secrets.token_urlsafe(64)
    ticket = {
        "user_id": request.user.id,
        "instance": instance.slug,
        "widget": widget_id,
    }
    cache = caches["ws_tickets"]
    cache.set(ticket_key, ticket, settings.WS_TICKET_EXPIRY)
    return JsonResponse({"ticket": ticket_key})








