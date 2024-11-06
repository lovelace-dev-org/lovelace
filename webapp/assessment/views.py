import json
from operator import itemgetter
import redis
import reversion
from django.conf import settings
from django.db.models import Prefetch
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
    JsonResponse,
)
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext as _

from courses.models import EmbeddedLink, UserAnswer, UserTaskCompletion, StudentGroup

from assessment.models import AssessmentBullet, AssessmentSheet, AssessmentToExerciseLink
from assessment.forms import (
    AddAssessmentForm,
    AssessmentBulletForm,
    AssessmentForm,
    NewBulletForm,
    SectionForm,
)
from assessment.utils import get_sectioned_sheet, serializable_assessment, copy_sheet

from utils.access import (
    ensure_owner_or_staff,
    ensure_staff,
)
from utils.content import get_embedded_parent
from utils.formatters import display_name


def view_assessment_sheet(request, course, instance, content):
    sheet_link = AssessmentToExerciseLink.objects.filter(
        exercise=content,
        instance=instance,
    ).first()
    if sheet_link:
        sheet, by_section = get_sectioned_sheet(sheet_link)
    else:
        by_section = {}
        sheet = None
    panel_t = loader.get_template("assessment/view_panel.html")
    panel_c = {"sheet": sheet, "bullets_by_section": by_section}
    return HttpResponse(panel_t.render(panel_c, request))


@ensure_staff
def manage_assessment(request, course, instance, content):
    course_sheets = AssessmentSheet.objects.filter(origin=course)
    sheet_link = AssessmentToExerciseLink.objects.filter(
        exercise=content,
        instance=instance,
    ).first()
    if request.method == "POST":
        form = AddAssessmentForm(request.POST, course_sheets=course_sheets)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        if form.cleaned_data["copy"]:
            source_sheet = AssessmentSheet.objects.get(id=form.cleaned_data["sheet"])
            new_sheet = AssessmentSheet(origin=course)
            for lang_code, __ in settings.LANGUAGES:
                field = "title_" + lang_code
                setattr(new_sheet, field, form.cleaned_data[field])
            with reversion.create_revision():
                new_sheet.save()
                copy_sheet(source_sheet, new_sheet)
                reversion.set_user(request.user)
            sheet = new_sheet
        else:
            try:
                sheet = AssessmentSheet.objects.get(id=form.cleaned_data["sheet"])
            except AssessmentSheet.DoesNotExist:
                with reversion.create_revision():
                    sheet = AssessmentSheet(origin=course)
                    for lang_code, __ in settings.LANGUAGES:
                        field = "title_" + lang_code
                        setattr(sheet, field, form.cleaned_data[field])
                    sheet.save()
                    reversion.set_user(request.user)

        if not sheet_link:
            sheet_link = AssessmentToExerciseLink(
                exercise=content, instance=instance, sheet=sheet, revision=None
            )
        else:
            sheet_link.sheet = sheet
        sheet_link.save()
        return JsonResponse({"status": "ok"})

    form = AddAssessmentForm(course_sheets=course_sheets)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": reverse(
            "assessment:manage_assessment",
            kwargs={"course": course, "instance": instance, "content": content},
        ),
        "html_id": content.slug + "-assessment-select",
        "html_class": "assessment-staff-form staff-only",
        "disclaimer": _("Add a new or existing assessment sheet to be used for this exercise."),
    }
    form_html = form_t.render(form_c, request)
    if sheet_link:
        sheet, by_section = get_sectioned_sheet(sheet_link)
    else:
        by_section = {}
        sheet = None
    panel_t = loader.get_template("assessment/management_panel.html")
    panel_c = {
        "course": course,
        "instance": instance,
        "exercise": content,
        "top_form": form_html,
        "sheet": sheet,
        "bullets_by_section": by_section,
    }
    return HttpResponse(panel_t.render(panel_c, request))


@ensure_staff
def create_bullet(request, course, instance, sheet):
    if request.method == "POST":
        form = NewBulletForm(request.POST)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        new_bullet = form.save(commit=False)
        new_bullet.sheet = sheet
        if form.cleaned_data.get("active_bullet"):
            active = AssessmentBullet.objects.get(id=form.cleaned_data["active_bullet"])
            new_bullet.section = active.section
            new_bullet.ordinal_number = active.ordinal_number + 1
        else:
            new_bullet.section_id = form.cleaned_data["active_section"]
            new_bullet.ordinal_number = 1
        bullets_after = AssessmentBullet.objects.filter(
            sheet=sheet,
            section=new_bullet.section,
            ordinal_number__gte=new_bullet.ordinal_number,
        ).order_by("ordinal_number")
        with reversion.create_revision():
            for bullet in bullets_after:
                bullet.ordinal_number += 1
                bullet.save()
            new_bullet.save()
            sheet.save()
            reversion.set_user(request.user)
        return JsonResponse({"status": "ok"})

    form = NewBulletForm()
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "assessment:create_bullet",
            kwargs={"course": course, "instance": instance, "sheet": sheet},
        ),
        "html_id": f"{sheet.id}-create-bullet",
        "html_class": "assessment-staff-form staff-only",
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def edit_section(request, course, instance, sheet, section=None):
    if request.method == "POST":
        form = SectionForm(request.POST, instance=section)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        with reversion.create_revision():
            section = form.save(commit=False)
            section.sheet = sheet
            section.save()
            sheet.save()
            reversion.set_user(request.user)
        return JsonResponse({"status": "ok"})

    form = SectionForm(instance=section)
    submit_key = "assessment:rename_section" if section else "assessment:create_section"
    submit_args = {
        "course": course,
        "instance": instance,
        "sheet": sheet,
    }
    if section:
        submit_args["section"] = section
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(submit_key, kwargs=submit_args),
        "html_id": f"{sheet.id}-rename-section",
        "html_class": "assessment-staff-form staff-only",
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def delete_section(request, course, instance, sheet, section):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    with reversion.create_revision():
        AssessmentBullet.objects.filter(sheet=sheet, section=section).delete()
        section.delete()
        sheet.save()
        reversion.set_user(request.user)
    return HttpResponse(status=204)


@ensure_staff
def move_bullet(request, course, instance, sheet, target_bullet, placement):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        active_bullet = AssessmentBullet.objects.get(id=request.POST["active_bullet"])
    except AssessmentBullet.DoesNotExist:
        return HttpResponseNotFound()

    if placement == "after":
        new_ordinal = target_bullet.ordinal_number + 1
    elif placement == "before":
        new_ordinal = target_bullet.ordinal_number
    else:
        return HttpResponseBadRequest()

    bullets_after = AssessmentBullet.objects.filter(
        sheet=sheet, section=target_bullet.section, ordinal_number__gte=new_ordinal
    ).order_by("ordinal_number")
    with reversion.create_revision():
        for bullet in bullets_after:
            bullet.ordinal_number += 1
            bullet.save()
        active_bullet.ordinal_number = new_ordinal
        active_bullet.section = target_bullet.section
        active_bullet.save()
        sheet.save()
        reversion.set_user(request.user)

    return JsonResponse({"status": "ok"})


@ensure_staff
def edit_bullet(request, course, instance, sheet, bullet):
    if request.method == "POST":
        form = AssessmentBulletForm(request.POST, instance=bullet)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        with reversion.create_revision():
            form.save(commit=True)
            sheet.save()
            reversion.set_user(request.user)
        return JsonResponse({"status": "ok"})

    form = AssessmentBulletForm(instance=bullet)
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "assessment:edit_bullet",
            kwargs={"course": course, "instance": instance, "sheet": sheet, "bullet": bullet},
        ),
        "html_id": f"{bullet.id}-edit-bullet",
        "html_class": "assessment-staff-form staff-only",
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def delete_bullet(request, course, instance, sheet, bullet):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    with reversion.create_revision():
        bullet.delete()
        reversion.set_user(request.user)
    return HttpResponse(status=204)


@ensure_staff
def update_exercise_points(request, course, instance, content, sheet):
    sheet_link = AssessmentToExerciseLink.objects.filter(
        exercise=content,
        instance=instance,
    ).first()

    with reversion.create_revision():
        content.default_points = sheet_link.calculate_max_score()
        content.save()
        reversion.set_user(request.user)

    embed_links = EmbeddedLink.objects.filter(embedded_page=content, instance=instance)
    for link in embed_links:
        link.parent.regenerate_cache(instance)

    return JsonResponse({"status": "ok"})


@ensure_staff
def view_submissions(request, course, instance, content):
    users = (
        instance.enrolled_users.get_queryset().order_by("last_name", "first_name", "username").all()
    )
    all_records = (
        UserTaskCompletion.objects.filter(
            instance=instance,
            exercise=content,
        )
        .exclude(state="credited")
        .prefetch_related(Prefetch("user", queryset=users))
    )
    assessed = []
    unassessed = []
    suspect = []
    skip = []
    for completion in all_records:
        try:
            if completion.user.id in skip:
                continue
        except UserTaskCompletion.user.RelatedObjectDoesNotExist:
            # this ignores completion objects from users that are not enrolled
            # e.g. staff members
            continue

        entry = {}
        if content.group_submission:
            try:
                group = StudentGroup.objects.get(members=completion.user, instance=instance)
            except StudentGroup.DoesNotExist:
                entry["group"] = "-"
                entry["students"] = display_name(completion.user)
            else:
                entry["group"] = group.name
                member_list = []
                for member in group.members.get_queryset():
                    member_list.append(display_name(member))
                    skip.append(member.id)
                entry["students"] = "\n".join(member_list)
        else:
            entry["group"] = "-"
            entry["students"] = display_name(completion.user)

        href_args = {
            "user": completion.user,
            "course": course,
            "instance": instance,
            "exercise": content,
        }
        entry["answers_url"] = reverse("courses:show_answers", kwargs=href_args)
        entry["assessment_url"] = reverse("assessment:submission_assessment", kwargs=href_args)
        if completion.state in ["correct", "incorrect"]:
            try:
                evaluated_answer = (
                    UserAnswer.get_task_answers(content, instance, completion.user)
                    .exclude(evaluation=None)
                    .exclude(evaluation__feedback="")
                    .latest("answer_date")
                )
            except UserAnswer.DoesNotExist:
                unassessed.append(entry)
            else:
                entry["total_points"] = evaluated_answer.evaluation.points
                if evaluated_answer.evaluation.suspect:
                    suspect.append(entry)
                else:
                    assessed.append(entry)
        else:
            unassessed.append(entry)

    assessed.sort(key=itemgetter("group"))
    unassessed.sort(key=itemgetter("group"))
    parent, single_linked = get_embedded_parent(content, instance)

    t = loader.get_template("assessment/submissions.html")
    c = {
        "course": course,
        "instance": instance,
        "course_staff": True,
        "exercise": content,
        "parent": parent,
        "single_linked": single_linked,
        "assessed": assessed,
        "unassessed": unassessed,
        "suspect": suspect,
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def submission_assessment(request, course, instance, exercise, user):
    try:
        sheet_link = AssessmentToExerciseLink.objects.get(instance=instance, exercise=exercise)
    except AssessmentToExerciseLink.DoesNotExist:
        return HttpResponseNotFound(_("Assessment sheet for this exercise doesn't exist"))

    sheet, by_section = get_sectioned_sheet(sheet_link)

    if request.method == "POST":
        form = AssessmentForm(request.POST, by_section=by_section)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        assessment = serializable_assessment(request.user, sheet, by_section, form.cleaned_data)
        answer_object = UserAnswer.get_task_answers(exercise, instance, user).latest("answer_date")
        exercise.update_evaluation(
            user,
            {
                "evaluation": form.cleaned_data.get("correct", False),
                "evaluator": request.user,
                "points": assessment["total_score"],
                "max": sheet_link.calculate_max_score(),
                "feedback": json.dumps(assessment),
                "suspect": form.cleaned_data.get("suspect", False),
                "comment": form.cleaned_data.get("comment", ""),
            },
            answer_object,
            complete=form.cleaned_data.get("complete", False),
            overwrite=True
        )
        return JsonResponse({"status": "ok"})

    try:
        evaluated_answer = (
            UserAnswer.get_task_answers(exercise, instance, user)
            .exclude(evaluation=None)
            .exclude(evaluation__feedback="")
            .latest("answer_date")
        )
        assessment = json.loads(evaluated_answer.evaluation.feedback)
        suspect = evaluated_answer.evaluation.suspect
        comment = evaluated_answer.evaluation.comment
    except (UserAnswer.DoesNotExist, json.JSONDecodeError):
        evaluated_answer = None
        assessment = {}
        suspect = False
        comment = ""

    max_score = 0
    section_scores = {}
    for section in assessment.get("sections", []):
        section_scores[section["name"]] = section["section_points"]

    for name, section in by_section.items():
        section["section_points"] = section_scores.get(name.title, 0)
        max_score += section["total_points"]

    parent, single_linked = get_embedded_parent(exercise, instance)

    form = AssessmentForm(
        by_section=by_section,
        assessment=assessment,
        initial={
            "suspect": suspect,
            "comment": comment,
        }
    )
    c = {
        "course": course,
        "instance": instance,
        "course_staff": True,
        "exercise": exercise,
        "parent": parent,
        "single_linked": single_linked,
        "user": user,
        "sheet": sheet,
        "bullets_by_section": by_section,
        "assessment": assessment,
        "form": form,
        "total_score": assessment.get("total_score", 0),
        "max_score": max_score,
    }

    t = loader.get_template("assessment/assessment_sheet.html")
    return HttpResponse(t.render(c, request))


@ensure_owner_or_staff
def view_assessment(request, user, course, instance, exercise, answer):
    if not exercise.manually_evaluated:
        return HttpResponseNotFound(_("This exercise does not have manual assessment."))

    try:
        assessment = json.loads(answer.evaluation.feedback)
    except AttributeError:
        return HttpResponseNotFound(_("This answer has not been evaluated"))
    except json.JSONDecodeError:
        return HttpResponseNotFound(_("Assessment not found"))

    t = loader.get_template("assessment/assessment_view.html")
    c = {"document": assessment}
    return HttpResponse(t.render(c, request))
