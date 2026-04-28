"""
Django views for rendering the course contents and checking exercises.
"""
import datetime
from decimal import Decimal
import json
import logging
import os
from html import escape
from collections import namedtuple
from operator import attrgetter

import redis
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseNotFound,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseBadRequest,
)
from django.db import transaction
from django.template import loader, engines
from django.conf import settings
from django.core.files.base import File
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from reversion.models import Version

from lovelace import plugins as lovelace_plugins
from lovelace.celery import app as celery_app
from courses import markupparser
import courses.tasks as rpc_tasks
from courses import blockparser
from courses.models import (
    About,
    Course,
    CourseEnrollment,
    CourseInstance,
    CourseMediaLink,
    ContentGraph,
    DeadlineExemption,
    EmbeddedLink,
    File,
    FileExerciseTestIncludeFile,
    FileUploadExerciseReturnFile,
    InvalidExerciseAnswerException,
    RepeatedTemplateExercise,
    RepeatedTemplateExerciseBackendFile,
    RepeatedTemplateExerciseSession,
    RepeatedTemplateExerciseSessionInstance,
    UserCheckboxExerciseAnswer,
    UserFileUploadExerciseAnswer,
    UserMultipleChoiceExerciseAnswer,
    UserRepeatedTemplateExerciseAnswer,
    UserTaskCompletion,
    UserTextfieldExerciseAnswer,
)
from utils.access import (
    block_in_exam_mode,
    is_course_staff,
    determine_media_access,
    ensure_enrolled_or_staff,
    ensure_owner_or_staff,
    determine_access,
)
from utils.archive import find_version_with_filename, get_single_archived
from utils.content import (
    check_exercise_accessible,
    system_messages,
    course_tree,
    first_title_from_content,
    get_answer_count_meta,
    get_embedded_parent,
)
from utils.exercise import compile_evaluation_data
from utils.files import find_fs_path, generate_download_response
from utils.notify import send_error_report, send_welcome_email
from utils.rendering import render_terms

JSON_INCORRECT = 0
JSON_CORRECT = 1
JSON_INFO = 2
JSON_ERROR = 3
JSON_DEBUG = 4

logger = logging.getLogger(__name__)

# PAGE VIEWS
# |
# v


@system_messages
def index(request):
    # This cannot be ordered on DB level because of translations
    course_list = list(Course.objects.all())

    def name_key(course):
        return course.name.lower()

    course_list.sort(key=name_key)
    t = loader.get_template("courses/index.html")
    c = {
        "course_list": course_list,
    }
    return HttpResponse(t.render(c, request))

@system_messages
def about(request):
    local_about = About.objects.first()
    parser = markupparser.MarkupParser()
    markup_gen = parser.parse(local_about.content)
    local_about_body = ""
    for chunk in markup_gen:
        if isinstance(chunk[1], str):
            local_about_body += chunk[1]
        else:
            raise ValueError("Embedded content is not allowed about page content")

    t = loader.get_template("courses/about.html")
    c = {
        "about_instance": local_about_body,
    }
    return HttpResponse(t.render(c, request))



@system_messages
def course_instances(request, course):
    try:
        primary = CourseInstance.objects.get(course=course, primary=True)
    except CourseInstance.DoesNotExist:
        t = loader.get_template("courses/error-page.html")
        c = {"error_msg": _("This course does not have a primary instance.")}
        return HttpResponse(t.render(c, request))

    return redirect(reverse("courses:course", kwargs={
        "course": course,
        "instance": primary,
    }))


@system_messages
def course(request, course, instance):
    enroll_state = instance.user_enroll_status(request.user)
    enrolled = enroll_state in ["ACCEPTED", "COMPLETED"]
    staff = is_course_staff(request.user, instance)

    if settings.EXAM_MODE and not enrolled and not staff:
        return HttpResponseForbidden(
            _("Only enrolled users can view this content in exam mode")
        )

    frontpage = instance.frontpage
    if frontpage:
        context = _page_context(request, course, instance, frontpage)
    else:
        context = {}

    context["course"] = course
    context["instance"] = instance
    context["enroll_state"] = enroll_state
    context["course_staff"] = staff

    if staff:
        view_mode = "staff"
    elif not enrolled:
        view_mode = "guest"
    elif settings.EXAM_MODE:
        view_mode = "exam"
    else:
        view_mode = None

    context["content_tree"] = instance.get_content_tree(
        mode=view_mode
    )

    if enrolled:
        user_results = dict(
            (entry["exercise_id"], entry) for entry in
            UserTaskCompletion.objects.filter(user=request.user, instance=instance).values()
        )
        exemptions = dict(
            (entry["contentgraph_id"], entry["new_deadline"]) for entry in
            DeadlineExemption.objects.filter(user=request.user).values()
        )
    else:
        user_results = {}
        exemptions = {}

    context["student_results"] = user_results
    context["exemptions"] = exemptions
    context["time_now"] = datetime.datetime.now()
    t = loader.get_template("courses/course.html")
    return HttpResponse(t.render(context, request))

def _page_context(request, course, instance, content, pagenum=None):
    content_graph = None
    revision = None
    try:
        content_graph = ContentGraph.objects.filter(instance=instance, content=content).first()
    except ContentGraph.DoesNotExist:
        return HttpResponseNotFound(
            _("Content {content} is not linked to course {course}!").format(
                content=content.slug, course=course.slug
            )
        )
    else:
        if content_graph is None:
            return HttpResponseNotFound(
                _("Content {content} is not linked to course {course}!").format(
                    content=content.slug, course=course.slug
                )
            )

    evaluation = None
    answer_count = None
    enrolled = False
    course_staff = False
    if request.user.is_authenticated:
        if (
            request.user.is_active
            and content.is_answerable()
            and content.get_user_answers(content, request.user, instance)
        ):
            answer_count = content.get_user_answers(content, request.user, instance).count()
        if content_graph and (
            content_graph.publish_date is None
            or content_graph.publish_date < datetime.datetime.now()
        ):
            try:
                evaluation = content.get_user_evaluation(request.user, instance)
            except NotImplementedError:
                evaluation = None
        try:
            if CourseEnrollment.objects.get(instance=instance, student=request.user).is_enrolled():
                enrolled = True
        except CourseEnrollment.DoesNotExist:
            pass
        if is_course_staff(request.user, instance):
            course_staff = True

    if not content_graph.visible and not course_staff:
        return HttpResponseNotFound(_("This content is (currently) only available to course staff"))

    if content_graph.require_enroll or content_graph.visibility == "exam-only":
        if not (enrolled or course_staff):
            return HttpResponseNotFound(_("This content is only available to enrolled users"))

    if settings.EXAM_MODE and content_graph.visibility == "no-exam":
        return HttpResponseNotFound(_("This content is not accessible in exam mode"))

    revision = content_graph.revision
    content_type = content.content_type
    context = {
        "course": course,
        "course_slug": course.slug,
        "instance": instance,
        "instance_slug": instance.slug,
        "content_page": content,
        "enrolled": enrolled,
        "course_staff": course_staff,
    }
    question = blockparser.parseblock(escape(content.question, quote=False), {"course": course})
    choices = content.get_choices(content, revision=revision)
    rendered_content = content.rendered_markup(request, context, revision, page=pagenum)
    termbank_contents, term_div_data = render_terms(request, instance, context)
    embedded_links = EmbeddedLink.objects.filter(parent=content, instance=instance).select_related(
        "embedded_page"
    )
    embed_dict = {}
    for link in embedded_links:
        embed_dict[link.embedded_page.slug] = link

    c = {
        "course": course,
        "course_slug": course.slug,
        "course_name": course.name,
        "instance": instance,
        "instance_name": instance.name,
        "instance_slug": instance.slug,
        "content": content,
        "content_blocks": rendered_content,
        "embedded_pages": embed_dict,
        "rendered_content": rendered_content,
        "embedded": False,
        "content_name": content.name,
        "content_type": content_type,
        "question": question,
        "choices": choices,
        "evaluation": evaluation,
        "answer_count": answer_count,
        "sandboxed": False,
        "termbank_contents": sorted(list(termbank_contents.items())),
        "term_div_data": term_div_data,
        "revision": revision,
        "enrolled": enrolled,
        "course_staff": course_staff,
        "editable_markups": markupparser.MarkupParser.editable_markups(),
        "edit_content_url": reverse("courses:content_edit_form", kwargs={
            "course": course,
            "instance": instance,
            "content": content,
            "action": "edit",
        }),
        "delete_content_url": reverse("courses:content_edit_form", kwargs={
            "course": course,
            "instance": instance,
            "content": content,
            "action": "delete",
        }),
        "add_content_url": reverse("courses:content_add_form", kwargs={
            "course": course,
            "instance": instance,
            "content": content,
        }),
    }
    return c


@system_messages
def content(request, course, instance, content, pagenum=None):
    c = _page_context(request, course, instance, content, pagenum=None)
    if not isinstance(c, dict):
        return c
    t = loader.get_template("courses/contentpage.html")
    return HttpResponse(t.render(c, request))


@ensure_owner_or_staff
@block_in_exam_mode
def show_answers(request, user, course, instance, parent, exercise):
    """
    Show the user's answers for a specific exercise on a specific course.
    """

    embed_link = EmbeddedLink.objects.get(embedded_page=exercise, instance=instance, parent=parent)
    completion = UserTaskCompletion.objects.filter(
        user=user, instance=instance, exercise=exercise
    ).first()
    content_type = exercise.content_type
    question = exercise.question
    choices = exercise.get_choices(exercise)
    template = exercise.answers_template

    answers = exercise.get_user_answers(exercise, user, instance)
    answers = answers.order_by("-answer_date")

    title, anchor = first_title_from_content(exercise.content)

    t = loader.get_template(template)
    c = {
        "exercise": exercise,
        "exercise_title": title,
        "course": course,
        "course_slug": course.slug,
        "course_name": course.name,
        "instance": instance,
        "instance_slug": instance.slug,
        "instance_name": instance.name,
        "instance_email": instance.email,
        "parent": parent,
        "embed_link": embed_link,
        "anchor": anchor,
        "answers_url": request.build_absolute_uri(),
        "answers": answers,
        "completion": completion,
        "student": user,
        "username": user.username,
        "course_staff": is_course_staff(request.user, instance),
        "enrolled_instances": CourseEnrollment.get_enrolled_instances(
            instance, user, exclude_current=True
        ),
    }
    return HttpResponse(t.render(c, request))


# ^
# |
# PAGE VIEWS
# CHECKING RELATED
# |
# v


@ensure_enrolled_or_staff
def check_answer(request, course, instance, parent, content):
    """
    Saves and evaluates a user's answer to an exercise and sends the results
    back to the user.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = request.user
    ip = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
    answer = request.POST
    files = request.FILES

    embed_link = EmbeddedLink.objects.get(embedded_page=content, instance=instance, parent=parent)

    if embed_link.revision is None:
        latest = Version.objects.get_for_object(content).latest("revision__date_created")
        answered_revision = latest.revision_id
        revision = None
        exercise = content
    else:
        answered_revision = revision
        exercise = get_single_archived(content, revision)

    answer_count = exercise.get_user_answers(exercise, user, instance).count()
    if embed_link.answer_limit is not None and answer_count >= embed_link.answer_limit:
        return JsonResponse({"result": _("You don't have any more attempts left for this task.")})

    try:
        answer_object = exercise.save_answer(
            content, user, ip, answer, files, instance, answered_revision
        )
    except InvalidExerciseAnswerException as e:
        return JsonResponse({"result": str(e)})

    answer_count += 1

    if embed_link.delayed_evaluation:
        evaluation = {"evaluation": False, "manual": True}
    else:
        evaluation = exercise.check_answer(
            content, embed_link, user, answer, files, answer_object
        )
        evaluation["points"] = Decimal(evaluation.get("quotient", 0)) * embed_link.default_points
        if embed_link.manually_evaluated:
            evaluation["manual"] = True
            evaluation["evaluation"] = False
            if exercise.content_type == "FILE_UPLOAD_EXERCISE":
                task_id = evaluation.get("task_id")
                if task_id is not None:
                    return check_progress(request, course, instance, parent, content, task_id)
                elif errors := evaluation.get("errors"):
                    return JsonResponse({"result": errors})
        else:
            evaluation["manual"] = False
            if exercise.content_type == "FILE_UPLOAD_EXERCISE":
                task_id = evaluation.get("task_id")
                if task_id is not None:
                    return check_progress(request, course, instance, parent, content, task_id)
                elif errors := evaluation.get("errors"):
                    print(errors)
                    return JsonResponse({"result": errors})

    exercise.save_evaluation(embed_link, user, evaluation, answer_object)

    msg_context = {
        "course_slug": course.slug,
        "instance_slug": instance.slug,
        "instance": instance,
        "content_page": content,
    }
    answer_count = exercise.get_user_answers(exercise, user, instance).count()
    answer_count_str = get_answer_count_meta(answer_count)
    answer_url = (
        reverse(
            "courses:show_answers",
            kwargs={
                "user": request.user,
                "course": course,
                "instance": instance,
                "parent": parent,
                "exercise": content,
            },
        )
        + "#"
        + str(answer_object.id)
    )
    evaluation["answer_url"] = request.build_absolute_uri(answer_url)
    evaluation["max"] = evaluation.get("max") or embed_link.default_points

    t = loader.get_template("courses/exercise-evaluation.html")
    total_evaluation, quotient = exercise.get_user_evaluation(user, instance)
    score = quotient * embed_link.default_points

    if not evaluation["evaluation"] or score < embed_link.default_points:
        parser = markupparser.MarkupParser()
        hints = [
            "".join(
                block[1] for block in parser.parse(msg, request, msg_context)
            ).strip()
            for msg in evaluation.get("hints", [])
        ]
    else:
        hints = []

    data = {
        "result": t.render(evaluation),
        "hints": hints,
        "evaluation": evaluation.get("evaluation"),
        "answer_count_str": answer_count_str,
        "attempts_left": embed_link.answer_limit and embed_link.answer_limit - answer_count,
        "total_evaluation": total_evaluation,
        "manual": embed_link.manually_evaluated or embed_link.delayed_evaluation,
        "score": f"{score:.2f}",
    }
    if "next_instance" in evaluation:
        data["next_instance"] = evaluation["next_instance"]
    if "total_instances" in evaluation:
        data["total_instances"] = evaluation["next_instance"]

    return JsonResponse(data)


# Legacy task type intended to be entirely phased out and replaced by routine exercise
@ensure_enrolled_or_staff
def get_repeated_template_session(request, course, instance, content, revision):
    check_results = check_exercise_accessible(request, course, instance, content)
    check_error = check_results.get("error")
    if check_error is not None:
        return check_error

    content = content.get_type_object()

    lang_code = translation.get_language()

    # If a user has an unfinished session, pick that one
    open_sessions = RepeatedTemplateExerciseSession.objects.filter(
        exercise=content,
        user=request.user,
        language_code=lang_code,
        repeatedtemplateexercisesessioninstance__userrepeatedtemplateinstanceanswer__isnull=True,
    )

    session = (
        open_sessions.exclude(
            repeatedtemplateexercisesessioninstance__userrepeatedtemplateinstanceanswer__correct=False
        )
        .distinct()
        .first()
    )

    if session is None:
        with transaction.atomic():
            session = RepeatedTemplateExerciseSession.objects.filter(
                exercise=content, user__isnull=True, language_code=lang_code
            ).first()
            if session is not None:
                session.user = request.user
                session.save()
            else:
                # create a new one, no need for atomic anymore
                if revision == "head":
                    revision = None
                celery_status = rpc_tasks.get_celery_worker_status()
                if "errors" in celery_status.keys():
                    data = {
                        "ready": True,
                        "rendered_template": _("Error, exercise backend unavailable."),
                    }
                else:
                    result = rpc_tasks.generate_repeated_template_session.delay(
                        user_id=request.user.id,
                        instance_id=instance.id,
                        exercise_id=content.id,
                        lang_code=lang_code,
                        revision=revision,
                    )
                    rerequest_url = reverse(
                        "courses:get_repeated_template_session",
                        kwargs={
                            "course": course,
                            "instance": instance,
                            "content": content,
                            "revision": "head" if revision is None else revision,
                        },
                    )
                    data = {
                        "ready": False,
                        "redirect": rerequest_url,
                    }
                return JsonResponse(data)

    # Pick the first unfinished instance
    session_instance = (
        RepeatedTemplateExerciseSessionInstance.objects.filter(
            session=session, userrepeatedtemplateinstanceanswer__isnull=True
        )
        .order_by("ordinal_number")
        .first()
    )

    session_template = session_instance.template
    variables = session_instance.variables
    values = session_instance.values

    total_instances = session.total_instances()
    next_instance = (
        session_instance.ordinal_number + 2
        if session_instance.ordinal_number + 1 < total_instances
        else None
    )

    rendered_template = session_instance.template.content_string.format(
        **dict(zip(variables, values))
    )

    template_context = {
        "course_slug": course.slug,
        "instance_slug": instance.slug,
    }
    parser = markupparser.MarkupParser()
    template_parsed = "".join(
        block[1] for block in parser.parse(rendered_template, request, template_context)
    ).strip()

    data = {
        "ready": True,
        "title": session_template.title,
        "rendered_template": template_parsed,
        "redirect": None,
        "next_instance": next_instance,
        "total_instances": total_instances,
        "progress": f"{session_instance.ordinal_number + 1} / {total_instances}",
    }

    return JsonResponse(data)


@ensure_enrolled_or_staff
def check_progress(request, course, instance, parent, content, task_id):
    # Based on https://djangosnippets.org/snippets/2898/
    task = celery_app.AsyncResult(id=task_id)
    info = task.info
    if task.ready():
        return file_exercise_evaluation(request, course, instance, parent, content, task_id, task)

    celery_status = rpc_tasks.get_celery_worker_status()
    if "errors" in celery_status:
        data = celery_status
    else:
        progress_url = reverse(
            "courses:check_progress",
            kwargs={
                "course": course,
                "instance": instance,
                "content": content,
                "parent": parent,
                "task_id": task_id,
            },
        )
        if not info:
            info = task.info  # Try again in case the first time was too early
        data = {"state": task.state, "metadata": info, "redirect": progress_url}
    return JsonResponse(data)


def file_exercise_evaluation(request, course, instance, parent, content, task_id, task=None):
    if task is None:
        task = celery_app.AsyncResult(task_id)

    embed_link = EmbeddedLink.objects.get(embedded_page=content, instance=instance, parent=parent)

    if embed_link.revision is not None:
        content = get_single_archived(content, revision)
    answers = content.get_user_answers(content, request.user, instance)
    answer_count = answers.count()
    evaluated_answer = answers.get(task_id=task_id)
    answer_count_str = get_answer_count_meta(answer_count)

    evaluation_tree = task.info["data"]
    evaluation_json = json.dumps(evaluation_tree)
    task.forget()

    evaluation_obj = content.save_evaluation(
        embed_link,
        request.user,
        {
            "evaluation": evaluation_tree["correct"],
            "test_results": evaluation_json,
            "manual": embed_link.manually_evaluated,
            "points": evaluation_tree["points"],
            "max": evaluation_tree["max"],
        },
        evaluated_answer,
    )

    answer_url = (
        reverse(
            "courses:show_answers",
            kwargs={
                "user": request.user,
                "course": course,
                "instance": instance,
                "parent": parent,
                "exercise": content,
            },
        )
        + "#"
        + str(evaluated_answer.id)
    )
    answer_url = request.build_absolute_uri(answer_url)
    msg_context = {
        "course_slug": course.slug,
        "instance_slug": instance.slug,
        "instance": instance,
        "content_page": content,
        "answer_url": answer_url,
        "embed_link": embed_link,
    }

    data = compile_evaluation_data(request, evaluation_tree, evaluation_obj, msg_context)

    errors = evaluation_tree["test_tree"].get("errors", [])
    if errors:
        if evaluation_tree["timedout"]:
            data["errors"] = _(
                "The program took too long to execute and was terminated. "
                "Check your code for too slow solutions."
            )
        else:
            data["errors"] = _(
                "Checking program was unable to finish due to an error. Contact course staff."
            )
            send_error_report(instance, content, revision, errors, answer_url)


    total_evaluation, quotient = content.get_user_evaluation(request.user, instance)
    score = quotient * embed_link.default_points

    data["answer_count_str"] = answer_count_str
    data["attempts_left"] = (embed_link.answer_limit and embed_link.answer_limit - answer_count,)
    data["manual"] = embed_link.manually_evaluated
    data["total_evaluation"] = (total_evaluation,)
    data["score"] = f"{score:.2f}"
    # data["has_faq"] = faq_utils.has_faq(instance, content, data["triggers"])
    data["extra_callbacks"] = []

    for module in lovelace_plugins["exercise-triggers"]:
        data["extra_callbacks"].extend(module.includes.get_exercise_trigger_callbacks(
            instance, content, data
        ))

    return JsonResponse(data)


# ^
# |
# CHECKING RELATED
# ANSWERS AJAX
# |
# v


@ensure_owner_or_staff
def get_file_exercise_evaluation(request, user, course, instance, parent, exercise, answer):
    embed_link = EmbeddedLink.objects.get(embedded_page=exercise, instance=instance, parent=parent)

    results_json = answer.evaluation.test_results
    evaluation_tree = json.loads(results_json)
    evaluation_obj = answer.evaluation

    msg_context = {
        "course_slug": course.slug,
        "instance_slug": instance.slug,
        "instance": instance,
        "content_page": exercise,
        "embed_link": embed_link,
    }

    data = compile_evaluation_data(request, evaluation_tree, evaluation_obj, msg_context)

    if not request.user.is_staff:
        data["triggers"] = []

    t_view = loader.get_template("courses/view-answer-results.html")

    return HttpResponse(t_view.render(data, request))


@ensure_owner_or_staff
def show_answer_file_content(request, user, course, instance, answer, filename):
    try:
        files = FileUploadExerciseReturnFile.objects.filter(answer=answer, answer__user=user)
    except FileUploadExerciseReturnFile.DoesNotExist as e:
        return HttpResponseForbidden(_("You cannot access this answer."))

    for f in files:
        if f.filename() == filename:
            content = f.get_content()
            break
    else:
        return HttpResponseForbidden(_("You cannot access this answer."))

    return HttpResponse(content)


# ^
# |
# ANSWERS AJAX
# DOWNLOAD VIEWS
# |
# v


@ensure_owner_or_staff
def download_answer_file(request, user, course, instance, answer, filename):
    try:
        files = FileUploadExerciseReturnFile.objects.filter(answer=answer, answer__user=user)
    except FileUploadExerciseReturnFile.DoesNotExist as e:
        return HttpResponseForbidden(_("You cannot access this answer."))

    for f in files:
        if f.filename() == filename:
            fs_path = os.path.join(
                getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT), f.fileinfo.name
            )
            break
    else:
        return HttpResponseForbidden(_("You cannot access this answer."))

    return generate_download_response(fs_path)


def download_embedded_file(request, course, instance, mediafile):
    """
    This view function is for downloading media files via the actual site.
    """

    file_link = CourseMediaLink.objects.filter(media=mediafile, instance=instance).first()
    if file_link is None:
        return HttpResponseNotFound(_("No such file {mediafile}").format(mediafile=mediafile.name))

    if file_link.revision is None:
        file_object = file_link.media.file
    else:
        file_object = get_single_archived(file_link.media.file, file_link.revision)
    fs_path = os.path.join(settings.MEDIA_ROOT, file_object.fileinfo.name)
    return generate_download_response(fs_path, file_object.download_as)


def download_media_file(request, file_slug, field_name, filename):
    """
    This view function is for downloading media files via the file admin interface.
    """

    # Try to find the file
    try:
        fileobject = File.objects.get(name=file_slug)
    except FileExerciseTestIncludeFile.DoesNotExist as e:
        return HttpResponseNotFound(_("Requested file does not exist."))

    if not determine_media_access(request.user, fileobject):
        return HttpResponseForbidden(
            _(
                "Only course main responsible teachers are allowed to "
                "download media files through this interface."
            )
        )

    try:
        fs_path = find_fs_path(filename, fileobject, field_name)
    except FileNotFoundError as e:
        return HttpResponseNotFound(e)

    return generate_download_response(fs_path)


def download_template_exercise_backend(request, exercise_id, field_name, filename):
    return download_exercise_backend(
        request, exercise_id, field_name, filename, RepeatedTemplateExerciseBackendFile
    )

# ^
# |
# DOWNLOAD VIEWS
# ENROLLMENT VIEWS
# |
# v


def enroll(request, course, instance):
    if not request.method == "POST":
        return HttpResponseNotAllowed(["POST"])

    form = request.POST

    if not request.user.is_authenticated:
        return HttpResponseForbidden(_("Only logged in users can enroll to courses."))

    if not request.user.userprofile.completed:
        response = JsonResponse({
            "message": _(
                "Your profile is not completed. "
                "Please fill in missing information in order to be eligible to enroll."
            )
        })
        response.set_cookie("profile_incomplete", "1", samesite="Strict")
        return response

    status = instance.user_enroll_status(request.user)

    if status not in [None, "WITHDRAWN"]:
        return HttpResponseBadRequest(_("You have already enrolled to this course."))

    with transaction.atomic():
        CourseEnrollment.objects.filter(instance=instance, student=request.user).delete()
        enrollment = CourseEnrollment(instance=instance, student=request.user)

        if not instance.manual_accept:
            enrollment.enrollment_state = "ACCEPTED"
            response_text = _("Your enrollment has been automatically accepted.")
            send_welcome_email(instance, user=request.user)
        else:
            enrollment.application_note = form.get("application-note")
            response_text = _("Your enrollment application has been registered for approval.")

        enrollment.save()

    return JsonResponse({"message": response_text})


def withdraw(request, course, instance):
    if not request.method == "POST":
        return HttpResponseNotAllowed(["POST"])

    if not request.user.is_authenticated:
        return HttpResponseForbidden(_("Only logged in users can manage their enrollments."))

    status = instance.user_enroll_status(request.user)

    if status is None:
        return HttpResponseBadRequest(_("You have not enrolled to this course."))

    with transaction.atomic():
        enrollment = CourseEnrollment.objects.get(instance=instance, student=request.user)
        enrollment.enrollment_state = "WITHDRAWN"
        enrollment.save()

    return JsonResponse({"message": _("Your enrollment has been withdrawn")})


# ^
# |
# ENROLLMENT VIEWS
# MISC VIEWS
# |
# v


def help_list(request):
    return HttpResponse()


def markup_help(request):
    markups = markupparser.MarkupParser.get_markups()
    Markup = namedtuple("Markup", ["name", "description", "example", "result", "slug"])

    parser = markupparser.MarkupParser()
    markup_list = (
        Markup(
            m.name,
            m.description,
            m.example,
            mark_safe(
                "".join(block[1] for block in parser.parse(m.example))
            ),
            slugify(m.name, allow_unicode=True),
        )
        for _, m in markups.items()
    )

    t = loader.get_template("courses/markup-help.html")
    c = {
        "markups": list(sorted(markup_list)),
    }
    return HttpResponse(t.render(c, request))


def terms(request):
    t = loader.get_template("courses/terms.html")
    c = {}
    return HttpResponse(t.render(c, request))
