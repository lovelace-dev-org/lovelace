import datetime
import os.path
import tempfile
import zipfile


from django.conf import settings
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseGone,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.template import loader
from django.urls import reverse
from django.utils import translation
from lovelace.celery import app as celery_app

from utils.access import determine_access, is_course_staff, ensure_responsible, ensure_staff
from utils.archive import get_single_archived
from utils.content import get_course_instance_tasks, get_embedded_parent
from utils.notify import send_welcome_email

from courses.forms import process_delete_confirm_form
from courses.models import (
    ContentGraph,
    CourseEnrollment,
    CourseInstance,
    DeadlineExemption,
    EmbeddedLink,
    FileUploadExerciseReturnFile,
    GradeThreshold,
    User,
    UserAnswer,
    UserTaskCompletion,
)
import teacher_tools.tasks as teacher_tasks
from teacher_tools.utils import (
    check_user_completion,
    compile_student_results,
    reconstruct_answer_form,
)
from teacher_tools.models import (
    MossBaseFile,
    MossSettings,
    ReminderTemplate,
)
from teacher_tools.forms import (
    DeadlineExemptionForm,
    MossnetForm,
    ReminderForm,
    BatchGradingForm,
    TransferRecordsForm,
)


def download_answers(request, course, instance, content):
    if not determine_access(request.user, content, responsible_only=True):
        return HttpResponseForbidden(
            _("Only course main responsible teachers are allowed to download answer files.")
        )

    files = FileUploadExerciseReturnFile.objects.filter(
        answer__exercise=content,
        answer__instance__course=course,
        answer__instance=instance,
    ).values_list("fileinfo", flat=True)

    errors = []

    with tempfile.TemporaryFile() as temp_storage:
        with zipfile.ZipFile(temp_storage, "w") as content_zip:
            for fileinfo in files:
                parts = fileinfo.split(os.path.sep)

                fs_path = os.path.join(
                    getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT), fileinfo
                )

                try:
                    content_zip.write(
                        fs_path.encode("utf-8"),
                        os.path.join(parts[2], parts[1], parts[4], parts[5]),
                    )
                except (IndexError, OSError) as e:
                    errors.append(fileinfo)

            if errors:
                error_str = "Zipping failed for these files:\n\n" + "\n".join(errors)
                content_zip.writestr(os.path.join(parts[2], "error_manifest"), error_str)

        temp_storage.seek(0)
        response = HttpResponse(temp_storage.read(), content_type="application/zip")

    response["Content-Disposition"] = f"attachment; filename={content.slug}_answers.zip"
    return response

#
#
#
# ENROLLMENT MANAGEMENT
# |
# v


def manage_enrollments(request, course, instance):
    if not is_course_staff(request.user, instance, responsible_only=True):
        return HttpResponseForbidden(
            _("Only course main responsible teachers are allowed to manage enrollments.")
        )

    if request.method == "POST":
        form = request.POST

        response = {}
        affected = []

        if "username" in form:
            username = form.get("username")
            with transaction.atomic():
                try:
                    enrollment = CourseEnrollment.objects.get(
                        student__username=username, instance=instance
                    )
                except CourseEnrollment.DoesNotExist:
                    response["msg"] = _("Enrollment for the student does not exist.")
                else:
                    enrollment.enrollment_state = form.get("action").upper()
                    enrollment.save()
                    response["msg"] = _(
                        "Enrollment status of {username} changed to {action}"
                    ).format(username=username, action=form.get("action"))
                    response["new_state"] = form.get("action").upper()
                    response["user"] = username
                    affected.append(username)

        else:
            usernames = form.getlist("selected-users")
            action = form.get("action")
            affected = []
            response["users-skipped"] = []
            response["affected-title"] = _(
                "Set enrollment state to {action} for the following users."
            ).format(action=action)
            response["skipped-title"] = _("The operation was not applicable for these users.")
            response["new_state"] = action.upper()

            with transaction.atomic():
                enrollments = CourseEnrollment.objects.filter(
                    student__username__in=usernames, instance=instance
                )

                for enrollment in enrollments:
                    if action == "accepted" and enrollment.enrollment_state == "WAITING":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    elif action == "denied" and enrollment.enrollment_state == "WAITING":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    elif action == "expelled" and enrollment.enrollment_state == "ACCEPTED":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    elif action == "accepted" and enrollment.enrollment_state == "EXPELLED":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    else:
                        response["users-skipped"].append(enrollment.student.username)

            response["users-affected"] = affected

        if form.get("action") == "accepted":
            userlist = User.objects.filter(username__in=affected)
            send_welcome_email(instance, userlist=userlist)

        return JsonResponse(response)

    users = instance.enrolled_users.get_queryset().order_by("last_name", "first_name", "username")

    enrollment_list = []

    for user in users:
        enrollment = CourseEnrollment.objects.get(student=user, instance=instance)
        enrollment_list.append((user, enrollment))

    t = loader.get_template("teacher_tools/manage_enrollments.html")
    c = {
        "course": course,
        "instance": instance,
        "enrollments": enrollment_list,
        "course_staff": True,
    }

    return HttpResponse(t.render(c, request))


@ensure_responsible
def transfer_records(request, course, instance, user):
    other_instances = (
        CourseInstance.objects.filter(course=course).exclude(id=instance.id).order_by("name")
    )

    if request.method == "POST":
        form = TransferRecordsForm(request.POST, instances=other_instances)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        target_instance = CourseInstance.objects.get(id=form.cleaned_data["target_instance"])
        model_classes = [
            UserAnswer,
            UserTaskCompletion,
        ]
        # NOTE: this should be replaced with a system that gets classes from registered task modules
        from routine_exercise.models import (
            RoutineExerciseProgress,
            RoutineExerciseQuestion,
        )

        model_classes.extend((RoutineExerciseQuestion, RoutineExerciseProgress))

        for model in model_classes:
            to_update = model.objects.filter(user=user, instance=instance).all()
            for obj in to_update:
                obj.instance = target_instance
                try:
                    obj.save()
                except IntegrityError:
                    obj.delete()

        CourseEnrollment.objects.filter(student=user, instance=instance).update(
            enrollment_state="TRANSFERED"
        )
        try:
            new_enrollment = CourseEnrollment.objects.get(student=user, instance=target_instance)
            new_enrollment.enrolled_state = "ACCEPTED"
        except CourseEnrollment.DoesNotExist:
            new_enrollment = CourseEnrollment(
                student=user, instance=target_instance, enrollment_state="ACCEPTED"
            )
        new_enrollment.save()

        if form.cleaned_data["recalculate"]:
            for __, task_links in get_course_instance_tasks(target_instance):
                for task_link in task_links:
                    content = task_link.embedded_page.get_type_object()
                    content.re_evaluate(user, target_instance)

        return redirect(
            reverse(
                "teacher_tools:manage_enrollments", kwargs={"course": course, "instance": instance}
            )
        )

    form = TransferRecordsForm(instances=other_instances)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_class": "side-panel-form",
        "disclaimer": _("Transfer records of {user} from {instance}").format(
            user=user.username,
            instance=instance.name,
        ),
        "submit_label": _("Execute"),
    }
    return HttpResponse(form_t.render(form_c, request))

# ^
# |
# ENROLLMENT MANAGEMENT
# COURSE COMPLETION
# |
# v



@ensure_staff
def answer_summary(request, course, instance, content):
    try:
        parent, single_linked = get_embedded_parent(content, instance)
    except EmbeddedLink.DoesNotExist:
        return HttpResponseNotFound(_("The task was not linked on the requested course instance"))

    answer_model = content.get_answer_model()
    answers = (
        answer_model.objects.filter(
            exercise=content,
            instance=instance,
        )
        .order_by("user", "-answer_date")
        .distinct("user")
    )

    t = loader.get_template("teacher_tools/answer_summary.html")
    c = {
        "course": course,
        "instance": instance,
        "content": content,
        "parent": parent,
        "single_linked": single_linked,
        "answers": answers,
        "course_staff": True,
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def student_course_completion(request, course, instance, user):
    tasks_by_page = get_course_instance_tasks(instance)
    results_by_page, total_points, total_missing, total_points_available = compile_student_results(
        user, instance, tasks_by_page
    )

    t = loader.get_template("teacher_tools/student_completion.html")
    c = {
        "student": user,
        "course": course,
        "instance": instance,
        "results_by_page": results_by_page,
        "total_missing": total_missing,
        "total_points": total_points,
        "total_points_available": total_points_available,
        "course_staff": True,
        "enrolled_instances": CourseEnrollment.get_enrolled_instances(
            instance, user, exclude_current=True
        ),
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def calculate_grades(request, course, instance):
    tasks_by_page = get_course_instance_tasks(instance)
    users = instance.enrolled_users.get_queryset()
    grade_thresholds = GradeThreshold.objects.filter(instance=instance).order_by("-threshold").all()
    grades_by_id = {}

    for user in users:
        by_page, total_points, total_missing, __ = compile_student_results(
            user, instance, tasks_by_page, summary=True
        )
        met_threshold = grade_thresholds.filter(threshold__lte=total_points).first()
        if met_threshold:
            grade = met_threshold.grade
        else:
            grade = ""

        grades_by_id[user.id] = {
            "missing": total_missing,
            "score": f"{total_points:.2f}",
            "grade": grade,
            "page_results": by_page,
        }

    return JsonResponse(grades_by_id)


@ensure_responsible
def course_completion_csv(request, course, instance):
    task = teacher_tasks.generate_completion_csv.delay(course.slug, instance.slug)
    return course_completion_csv_progress(request, course, instance, task.id)


@ensure_responsible
def course_completion_csv_progress(request, course, instance, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if not task.ready():
        progress_url = reverse(
            "teacher_tools:completion_csv_progress",
            kwargs={"course": course, "instance": instance, "task_id": task_id},
        )

        data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
        return JsonResponse(data)

    download_url = reverse(
        "teacher_tools:completion_csv_download",
        kwargs={"course": course, "instance": instance, "task_id": task_id},
    )
    data = {"state": task.state, "metadata": task.info, "redirect": download_url}
    return JsonResponse(data)


@ensure_responsible
def course_completion_csv_download(request, course, instance, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if not task.ready():
        return HttpResponseGone(
            _("Completion CSV generation (task id: {}) has already been downloaded.").format(
                task_id
            )
        )

    csv_str = cache.get(task_id)
    cache.delete(task_id)
    task.forget()
    response = HttpResponse(content=csv_str, content_type="text/csv")
    response[
        "Content-Disposition"
    ] = f"attachment; filename={instance.slug}_completion_{datetime.date.today():%Y-%m-%d}.csv"
    return response


@ensure_staff
def course_completion(request, course, instance):
    users = (
        instance.enrolled_users.get_queryset()
        .filter(courseenrollment__enrollment_state="ACCEPTED")
        .order_by("last_name", "first_name", "username")
    )

    t = loader.get_template("teacher_tools/course_completion.html")
    c = {"course": course, "instance": instance, "users": users, "course_staff": True}
    return HttpResponse(t.render(c, request))


# ^
# |
# COURSE COMPLETION
# REMINDERS
# |
# v


@ensure_responsible
def manage_reminders(request, course, instance):
    saved_template = ReminderTemplate.objects.filter(instance=instance).first()
    if request.method != "POST":
        form = ReminderForm(request.POST, instance=saved_template)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        if form.cleaned_data["reminder_action"] == "generate":
            if form.cleaned_data.get("save_template"):
                template = form.save(commit=False)
                template.instance = instance
                template.save()

            users = (
                instance.enrolled_users.get_queryset()
                .filter(courseenrollment__enrollment_state="ACCEPTED")
                .order_by("last_name", "first_name", "username")
            )

            tasks_by_page = get_course_instance_tasks(instance, datetime.datetime.now())

            reminder_list = []
            for user in users:
                missing_str = ""
                missing_count = 0
                completion_qs = UserTaskCompletion.objects.filter(user=user, instance=instance)
                for page, task_links in tasks_by_page:
                    page_stats = check_user_completion(
                        user, task_links, instance, completion_qs, include_links=False
                    )
                    missing_list = []
                    for result in page_stats:
                        if not result["correct"]:
                            missing_list.append(result["eo"])
                            missing_count += 1
                    if missing_list:
                        missing_str += " / ".join(
                            getattr(page, "name_" + code) or "" for code, lang in settings.LANGUAGES
                        ).lstrip(" /")
                        task_strs = []
                        for task in missing_list:
                            task_strs.append(
                                " / ".join(
                                    getattr(task, "name_" + code) or ""
                                    for code, lang in settings.LANGUAGES
                                ).lstrip(" /")
                            )
                        missing_str += "\n  " + "\n  ".join(task_strs) + "\n"
                if missing_str:
                    reminder_data = {
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "missing_count": missing_count,
                        "missing_str": missing_str,
                    }
                    reminder_list.append(reminder_data)

            reminder_cache = {
                "generated": datetime.date.today().strftime("%Y-%m-%d"),
                "reminders": reminder_list,
                "progress": 0,
            }
            cache.set(
                f"{instance.slug}_reminders",
                reminder_cache,
                timeout=settings.REDIS_LONG_EXPIRE,
            )

            return JsonResponse({"reminders": reminder_list, "submit_text": _("Send emails")})

        title = form.cleaned_data.get("title", "")
        header = form.cleaned_data.get("header", "")
        footer = form.cleaned_data.get("footer", "")
        task = teacher_tasks.send_reminder_emails.delay(
            course.slug, instance.slug, title, header, footer
        )
        return reminders_progress(request, course, instance, task.id)

    form = ReminderForm(instance=saved_template)
    reminders = cache.get(f"{instance.slug}_reminders")
    t = loader.get_template("teacher_tools/manage_reminders.html")
    c = {
        "course": course,
        "instance": instance,
        "form": form,
        "course_staff": True,
        "cached_reminders": reminders,
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def load_reminders(request, course, instance):
    reminder_cache = cache.get(f"{instance.slug}_reminders")
    if reminder_cache is None:
        return HttpResponseNotFound(_("Unable to retrieve cached reminders."))

    return JsonResponse({"reminders": reminder_cache["reminders"], "submit_text": _("Send emails")})


@ensure_responsible
def discard_reminders(request, course, instance):
    cache.delete(f"{instance.slug}_reminders")
    return JsonResponse({"success": True, "submit_text": _("Generate reminders")})


@ensure_responsible
def reminders_progress(request, course, instance, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        data = {"state": task.state, "metadata": task.info}
        return JsonResponse(data)

    progress_url = reverse(
        "teacher_tools:reminders_progress",
        kwargs={"course": course, "instance": instance, "task_id": task_id},
    )

    data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
    return JsonResponse(data)


# ^
# |
# REMINDERS
# GRADING TOOLS
# |
# v


@ensure_responsible
def batch_grade_task(request, course, instance, content):
    if content.content_type not in [
        "TEXTFIELD_EXERCISE",
        "CHECKBOX_EXERCISE",
        "MULTIPLE_CHOICE_EXERCISE",
        "MULTIPLE_QUESTION_EXAM",
    ]:
        return HttpResponseForbidden(_("Batch grading is not supported for this task type"))

    if content.manually_evaluated:
        return HttpResponseForbidden(
            _("Batch grading is not possible for manually evaluated tasks")
        )

    if request.method == "POST":
        form = BatchGradingForm(request.POST)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        try:
            parent, single_linked = get_embedded_parent(content, instance)
        except EmbeddedLink.DoesNotExist:
            return HttpResponseNotFound(
                _("The task was not linked on the requested course instance")
            )

        link = EmbeddedLink.objects.filter(instance=instance, embedded_page=content).first()
        if link is None:
            return HttpResponseNotFound(_("Task is not linked to this course"))

        if link.revision is None:
            exercise = content
        else:
            exercise = get_single_archived(content, link.revision)

        print(exercise)

        answer_model = content.get_answer_model()
        answers = (
            answer_model.objects.filter(
                exercise=content,
                instance=instance,
            )
            .order_by("user", "-answer_date")
            .all()
        )
        users = instance.enrolled_users.get_queryset().filter(
            courseenrollment__enrollment_state="ACCEPTED"
        )

        current_lang = translation.get_language()

        log = []

        for user in users:
            user_answers = answers.filter(user=user)
            if not user_answers:
                continue

            if form.cleaned_data["mode"] == "latest":
                user_answers = [user_answers.first()]

            for answer in user_answers:
                translation.activate(answer.language_code)
                answer_form = reconstruct_answer_form(exercise.content_type, answer)

                evaluation = exercise.check_answer(
                    content, user, answer.answerer_ip, answer_form, [], answer, link.revision
                )
                if evaluation["evaluation"]:
                    exercise.update_evaluation(user, evaluation, answer)
                    log.append(answer)
                    break
            else:
                evaluation["points"] = 0
                exercise.update_evaluation(user, evaluation, user_answers[0])
                log.append(user_answers[0])

        translation.activate(current_lang)

        t = loader.get_template("teacher_tools/answer_summary.html")
        c = {
            "course": course,
            "instance": instance,
            "content": content,
            "parent": parent,
            "single_linked": single_linked,
            "answers": log,
            "course_staff": True,
        }
        return HttpResponse(t.render(c, request))

    form = BatchGradingForm()
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_class": "side-panel-form",
        "disclaimer": _("Perform batch grading for {content}").format(content=content.name),
        "submit_label": _("Execute"),
    }
    return HttpResponse(form_t.render(form_c, request))


@ensure_responsible
def reset_completion(request, course, instance, content):
    if content.content_type not in [
        "TEXTFIELD_EXERCISE",
        "CHECKBOX_EXERCISE",
        "MULTIPLE_CHOICE_EXERCISE",
    ]:
        return HttpResponseForbidden(_("Completion reset is not supported for this task type"))

    if content.manually_evaluated:
        return HttpResponseForbidden(
            _("Completion reset is not possible for manually evaluated tasks")
        )

    try:
        parent, single_linked = get_embedded_parent(content, instance)
    except EmbeddedLink.DoesNotExist:
        return HttpResponseNotFound(_("The task was not linked on the requested course instance"))

    count, __ = UserTaskCompletion.objects.filter(instance=instance, exercise=content).delete()
    t = loader.get_template("teacher_tools/reset_completion.html")
    c = {
        "course": course,
        "instance": instance,
        "content": content,
        "parent": parent,
        "single_linked": single_linked,
        "count": count,
        "course_staff": True,
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def exercise_plagiarism(request, course, instance, content):
    saved_settings = MossSettings.objects.filter(exercise=content).first()
    other_instances = CourseInstance.objects.filter(course=course).exclude(pk=instance.pk)
    current_url = cache.get(f"{content.slug}_moss_result")

    if request.method == "POST":
        form = MossnetForm(request.POST, other_instances=other_instances, instance=saved_settings)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        if form.cleaned_data["save_settings"]:
            settings = form.save(commit=False)
            settings.exercise = content
            settings.save()

        if request.FILES:
            if form.cleaned_data["save_settings"]:
                MossBaseFile.objects.filter(moss_settings=settings).delete()
            for f in request.FILES.getlist("base_files"):
                base_file = MossBaseFile(fileinfo=f, exercise=content)
                if form.cleaned_data["save_settings"]:
                    base_file.moss_settings = settings
                base_file.save()

        task = teacher_tasks.order_moss_report.delay(
            course.slug, instance.slug, content.slug, form.cleaned_data
        )
        return moss_progress(request, course, instance, content, task.id)

    form = MossnetForm(other_instances=other_instances, instance=saved_settings)
    t = loader.get_template("teacher_tools/exercise_plagiarism.html")
    c = {
        "course": course,
        "instance": instance,
        "exercise": content,
        "course_staff": True,
        "form": form,
        "current_url": current_url,
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def moss_progress(request, course, instance, content, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        data = {"state": task.state, "metadata": task.info}
        return JsonResponse(data)

    progress_url = reverse(
        "teacher_tools:moss_progress",
        kwargs={"course": course, "instance": instance, "content": content, "task_id": task_id},
    )
    data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
    return JsonResponse(data)


# ^
# |
# GRADING TOOLS
# DEADLINE EXEMPTIONS
# |
# v


@ensure_responsible
def manage_exemptions(request, course, instance):
    exemptions = DeadlineExemption.objects.filter(
        contentgraph__instance=instance
    )
    t = loader.get_template("teacher_tools/deadline-exemptions.html")
    c = {
        "course": course,
        "instance": instance,
        "course_staff": True,
        "exemptions": exemptions,
    }
    return HttpResponse(t.render(c, request))

@ensure_responsible
def create_exemption(request, course, instance):
    students = instance.enrolled_users.get_queryset()
    graphs = (
        ContentGraph.objects.filter(instance=instance)
        .exclude(deadline=None)
    )
    if request.method == "POST":
        form = DeadlineExemptionForm(
            request.POST,
            students=students,
            graphs=graphs,
        )
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        form.save(commit=True)
        return JsonResponse({"status": "ok"})

    form = DeadlineExemptionForm(
        students=students,
        graphs=graphs
    )
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": f"create-exemption-form",
        "html_class": "management-form",
    }
    return HttpResponse(form_t.render(form_c, request))

@ensure_responsible
def delete_exemption(request, course, instance, user, graph_id):
    def success(form):
        DeadlineExemption.objects.filter(
            user=user,
            contentgraph__id=graph_id,
        ).delete()
    return process_delete_confirm_form(request, success)









