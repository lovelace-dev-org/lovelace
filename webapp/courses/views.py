"""
Django views for rendering the course contents and checking exercises.
"""
import datetime
import json
import logging
import os
from html import escape
from collections import namedtuple

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

from lovelace.celery import app as celery_app
import courses.tasks as rpc_tasks
from courses import markupparser
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
import faq.utils as faq_utils
from utils.access import (
    is_course_staff,
    determine_media_access,
    ensure_enrolled_or_staff,
    ensure_owner_or_staff,
    determine_access,
)
from utils.archive import find_version_with_filename, get_single_archived
from utils.content import (
    check_exercise_accessible,
    cookie_law,
    course_tree,
    first_title_from_content,
    get_answer_count_meta,
    get_embedded_parent,
)
from utils.exercise import compile_evaluation_data
from utils.files import generate_download_response
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


@cookie_law
def index(request):
    course_list = Course.objects.order_by("name").all()

    t = loader.get_template("courses/index.html")
    c = {
        "course_list": course_list,
    }
    return HttpResponse(t.render(c, request))

@cookie_law
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



@cookie_law
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


@cookie_law
def course(request, course, instance):
    frontpage = instance.frontpage
    if frontpage:
        context = content(request, course, instance, frontpage, frontpage=True)
    else:
        context = {}

    context["course"] = course
    context["instance"] = instance

    if is_course_staff(request.user, instance):
        content_qs = ContentGraph.objects.filter(
            instance=instance, ordinal_number__gt=0
        )
        context["course_staff"] = True
    else:
        content_qs = ContentGraph.objects.filter(
            instance=instance, ordinal_number__gt=0, visible=True
        )
        context["course_staff"] = False

    enroll_state = instance.user_enroll_status(request.user)
    enrolled = enroll_state in ["ACCEPTED", "COMPLETED"]
    context["enroll_state"] = enroll_state

    context["content_tree"] = instance.get_content_tree(staff=context["course_staff"])
    if request.user.is_authenticated:
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


@cookie_law
def content(request, course, instance, content, pagenum=None, **kwargs):
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

    if content_graph.require_enroll:
        if not (enrolled or course_staff):
            return HttpResponseNotFound(_("This content is only available to enrolled users"))

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
        embed_dict[link.embedded_page.slug] = link.embedded_page

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
        "uneditable_markups": settings.UNEDITABLE_MARKUPS,
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
    if "frontpage" in kwargs:
        return c

    t = loader.get_template("courses/contentpage.html")
    return HttpResponse(t.render(c, request))


@ensure_owner_or_staff
def show_answers(request, user, course, instance, exercise):
    """
    Show the user's answers for a specific exercise on a specific course.
    """

    try:
        parent, single_linked = get_embedded_parent(exercise, instance)
    except EmbeddedLink.DoesNotExist:
        return HttpResponseNotFound(_("The task was not linked on the requested course instance"))

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
        "single_linked": single_linked,
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
def check_answer(request, course, instance, content, revision):
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

    if revision == "head":
        latest = Version.objects.get_for_object(content).latest("revision__date_created")
        answered_revision = latest.revision_id
        revision = None
        exercise = content
    else:
        answered_revision = revision
        exercise = get_single_archived(content, revision)

    answer_count = exercise.get_user_answers(exercise, user, instance).count()
    if exercise.answer_limit is not None and answer_count >= exercise.answer_limit:
        return JsonResponse({"result": _("You don't have any more attempts left for this task.")})

    try:
        answer_object = exercise.save_answer(
            content, user, ip, answer, files, instance, answered_revision
        )
    except InvalidExerciseAnswerException as e:
        return JsonResponse({"result": str(e)})

    answer_count += 1

    if exercise.delayed_evaluation:
        evaluation = {"evaluation": False, "manual": True}
    else:
        evaluation = exercise.check_answer(
            content, user, ip, answer, files, answer_object, revision
        )
        if exercise.manually_evaluated:
            evaluation["manual"] = True
            evaluation["evaluation"] = False
            if exercise.content_type == "FILE_UPLOAD_EXERCISE":
                task_id = evaluation.get("task_id")
                if task_id is not None:
                    return check_progress(request, course, instance, content, revision, task_id)
        else:
            evaluation["manual"] = False
            if exercise.content_type == "FILE_UPLOAD_EXERCISE":
                task_id = evaluation.get("task_id")
                if task_id is not None:
                    return check_progress(request, course, instance, content, revision, task_id)

    exercise.save_evaluation(user, evaluation, answer_object)

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
                "exercise": content,
            },
        )
        + "#"
        + str(answer_object.id)
    )
    evaluation["answer_url"] = request.build_absolute_uri(answer_url)
    evaluation["max"] = evaluation.get("max") or exercise.default_points

    t = loader.get_template("courses/exercise-evaluation.html")
    total_evaluation, quotient = exercise.get_user_evaluation(user, instance)
    score = quotient * exercise.default_points

    if not evaluation["evaluation"] or score < exercise.default_points:
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
        "attempts_left": exercise.answer_limit and exercise.answer_limit - answer_count,
        "total_evaluation": total_evaluation,
        "manual": exercise.manually_evaluated or exercise.delayed_evaluation,
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
def check_progress(request, course, instance, content, revision, task_id):
    # Based on https://djangosnippets.org/snippets/2898/
    task = celery_app.AsyncResult(id=task_id)
    info = task.info
    if task.ready():
        return file_exercise_evaluation(request, course, instance, content, revision, task_id, task)

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
                "revision": "head" if revision is None else revision,
                "task_id": task_id,
            },
        )
        if not info:
            info = task.info  # Try again in case the first time was too early
        data = {"state": task.state, "metadata": info, "redirect": progress_url}
    return JsonResponse(data)


def file_exercise_evaluation(request, course, instance, content, revision, task_id, task=None):
    if task is None:
        task = celery_app.AsyncResult(task_id)
    if revision != "head":
        content = get_single_archived(content, revision)
    answers = content.get_user_answers(content, request.user, instance)
    answer_count = answers.count()
    evaluated_answer = answers.get(task_id=task_id)
    answer_count_str = get_answer_count_meta(answer_count)

    evaluation_tree = task.info["data"]
    evaluation_json = json.dumps(evaluation_tree)
    task.forget()
    evaluation_obj = content.save_evaluation(
        request.user,
        {
            "evaluation": evaluation_tree["correct"],
            "test_results": evaluation_json,
            "manual": content.manually_evaluated,
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
    score = quotient * content.default_points

    data["answer_count_str"] = answer_count_str
    data["attempts_left"] = (content.answer_limit and content.answer_limit - answer_count,)
    data["manual"] = content.manually_evaluated
    data["total_evaluation"] = (total_evaluation,)
    data["score"] = f"{score:.2f}"
    data["has_faq"] = faq_utils.has_faq(instance, content, data["triggers"])

    return JsonResponse(data)


# ^
# |
# CHECKING RELATED
# ANSWERS AJAX
# |
# v


@ensure_owner_or_staff
def get_file_exercise_evaluation(request, user, course, instance, exercise, answer):
    results_json = answer.evaluation.test_results
    evaluation_tree = json.loads(results_json)
    evaluation_obj = answer.evaluation

    msg_context = {
        "course_slug": course.slug,
        "instance_slug": instance.slug,
        "instance": instance,
        "content_page": exercise,
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
        if filename == os.path.basename(getattr(fileobject, field_name).name):
            fs_path = os.path.join(settings.MEDIA_ROOT, getattr(fileobject, field_name).name)
        else:
            # Archived file was requested
            version = find_version_with_filename(fileobject, field_name, filename)
            if version:
                filename = version.field_dict[field_name].name
                fs_path = os.path.join(settings.MEDIA_ROOT, filename)
            else:
                return HttpResponseNotFound(_("Requested file does not exist."))
    except AttributeError as e:
        return HttpResponseNotFound(_("Requested file does not exist."))

    return generate_download_response(fs_path)


def download_template_exercise_backend(request, exercise_id, field_name, filename):
    try:
        exercise_object = RepeatedTemplateExercise.objects.get(id=exercise_id)
    except CourseInstance.DoesNotExist as e:
        return HttpResponseNotFound(_("This exercise does't exist"))

    if not determine_access(request.user, exercise_object):
        return HttpResponseForbidden(
            _(
                "Only course main responsible teachers are "
                "allowed to download files through this interface."
            )
        )

    fileobjects = RepeatedTemplateExerciseBackendFile.objects.filter(exercise=exercise_object)
    try:
        for fileobject in fileobjects:
            if filename == os.path.basename(getattr(fileobject, field_name).name):
                fs_path = os.path.join(
                    settings.PRIVATE_STORAGE_FS_PATH, getattr(fileobject, field_name).name
                )
                break

            # Archived file was requested
            version = find_version_with_filename(fileobject, field_name, filename)
            if version:
                filename = version.field_dict[field_name].name
                fs_path = os.path.join(settings.PRIVATE_STORAGE_FS_PATH, filename)
                break
        else:
            return HttpResponseNotFound(_("Requested file does not exist."))
    except AttributeError as e:
        return HttpResponseNotFound(_("Requested file does not exist."))

    return generate_download_response(fs_path)


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
