import colorsys
import datetime
import itertools
import json
import re
import math
import statistics

from celery import chain
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden, JsonResponse
from django.template import loader
from django.utils.translation import gettext as _
from lovelace.celery import app as celery_app


from courses.models import (
    CheckboxExerciseAnswer,
    ContentPage,
    Course,
    CourseInstance,
    EmbeddedLink,
    Evaluation,
    MultipleChoiceExerciseAnswer,
    User,
    UserCheckboxExerciseAnswer,
    UserFileUploadExerciseAnswer,
    UserMultipleChoiceExerciseAnswer,
    UserRepeatedTemplateExerciseAnswer,
    UserRepeatedTemplateInstanceAnswer,
    UserTextfieldExerciseAnswer,
)
from utils.access import ensure_responsible

import stats.tasks as stat_tasks
from .models import TaskSummary


NO_USERS_MSG = "No users to calculate!"


def user_evaluation(user, exercise):
    return exercise.get_type_object().get_user_evaluation(exercise, user)


def user_has_answered(user, exercise):
    return user_evaluation(user, exercise) != "unanswered"


def course_exercises_with_color(course, instance):
    exercises = []
    parent_pages = instance.contents.select_related("content").order_by("ordinal_number")
    cg = color_generator(parent_pages.count())

    for p in parent_pages:
        color = next(cg)
        if p.content.embedded_pages.count() > 0:
            all_pages = list(
                p.content.embedded_pages.all().order_by("emb_embedded__ordinal_number")
            )
            exercises.extend(list(zip(itertools.cycle([color]), all_pages)))
    return exercises


def course_instance_exercises(course_inst):
    exercises = []

    parent_pages = course_inst.contents.select_related("content").order_by("ordinal_number")

    for p in parent_pages:
        if p.content.embedded_pages.count() > 0:
            all_pages = list(
                p.content.embedded_pages.all().order_by("emb_embedded__ordinal_number")
            )
            exercises.extend(all_pages)
    return exercises


def filter_users_enrolled(users, course_inst):
    return [user for user in users if user in course_inst.enrolled_users.all()]


def course_instances_linked(exercise):
    links = EmbeddedLink.objects.filter(embedded_page=exercise)
    return [link.instance for link in links]


###########################################################


def textfield_eval(given, answers):
    given_answer = given.replace("\r", "")
    correct = False
    hinted = False
    matches = []

    re_validate = lambda db_ans, given_ans: re.match(db_ans, given_ans) is not None
    str_validate = lambda db_ans, given_ans: db_ans == given_ans

    for answer in answers:
        validate = re_validate if answer.regexp else str_validate

        try:
            match = validate(answer.answer, given_answer)
        except re.error as e:
            matches.append((answer.answer, e))
            correct = False
            continue

        if match and answer.correct:
            correct = True
            matches.append((answer.answer, ""))
        elif match and not answer.correct:
            matches.append((answer.answer, ""))
            if answer.hint:
                hinted = True

    return (correct, hinted, matches)


def answers_average(answer_count, user_count):
    """
    Calculates the average of the number of answers per user.
    """

    try:
        return round(answer_count / user_count, 2)
    except ZeroDivisionError as e:
        raise ZeroUsersException("No users to calculate average answer count!") from e


def answers_standard_distrib(user_count, answers_avg, answer_counts):
    """
    Calculates the standard distribution of the number of answers per user.
    """

    deviations_squared = ((ac - answers_avg) ** 2 for ac in answer_counts)
    try:
        variance = (1 / user_count) * sum(deviations_squared)
    except ZeroDivisionError as e:
        raise ZeroUsersException("No users to calculate standard deviation!") from e
    return round(math.sqrt(variance), 2)


def exercise_answer_piechart(correct, incorrect, not_answered, canvas_id):
    """
    Shows statistics of correct and incorrect answers of a single exercise in a pie chart.
    """

    total = correct + incorrect + not_answered
    try:
        correct_pct = correct / total
        incorrect_pct = incorrect / total
        not_answered_pct = not_answered / total
    except ZeroDivisionError as e:
        raise ZeroUsersException("No users to create piechart!") from e
    # correct_deg = round(correct_pct * 360)
    # incorrect_deg = round(incorrect_pct * 360)
    # not_answered_deg = 360 - correct_deg - incorrect_deg

    return {
        "correct_n": correct,
        "incorrect_n": incorrect,
        "not_answered_n": not_answered,
        "correct_pct": round(correct_pct * 100),
        "incorrect_pct": round(incorrect_pct * 100),
        "not_answered_pct": round(not_answered_pct * 100),
        "canvas_id": canvas_id,
    }


def exercise_basic_answer_stats(exercise, users, answers, course_inst=None):
    correctly_by = 0
    incorrectly_by = 0
    users_answered = set()
    answer_count = answers.count()
    user_answers = set()
    for user, evaluation in answers.values_list("user", "evaluation"):
        try:
            user_answers.add((user, Evaluation.objects.get(id=evaluation).correct))
        except Evaluation.DoesNotExist:
            user_answers.add((user, False))

    for user in users:
        if (user.id, True) in user_answers:
            correctly_by += 1
            users_answered.add(user)
        elif (user.id, False) in user_answers:
            incorrectly_by += 1
            users_answered.add(user)

    user_count = len(users_answered)
    unanswered = len(users) - user_count
    answer_userids = list(answers.values_list("user", flat=True))
    user_answer_counts = [answer_userids.count(user.id) for user in users_answered]

    try:
        answers_avg = answers_average(answer_count, user_count)
    except ZeroUsersException:
        answers_avg = None
        answers_sd = None
    else:
        answers_sd = answers_standard_distrib(user_count, answers_avg, user_answer_counts)

    try:
        answers_median = statistics.median(user_answer_counts)
    except statistics.StatisticsError:
        answers_median = None

    basic_stats = {
        "answer_count": answer_count,
        "user_count": user_count,
        "answers_avg": round(answers_avg, 4) if answers_avg is not None else NO_USERS_MSG,
        "answers_sd": round(answers_sd, 4) if answers_sd is not None else NO_USERS_MSG,
        "answers_median": answers_median if answers_median is not None else NO_USERS_MSG,
        "correctly_by": correctly_by,
    }

    if course_inst is not None:
        canvas_id = course_inst.slug
    else:
        canvas_id = ""

    try:
        piechart = exercise_answer_piechart(correctly_by, incorrectly_by, unanswered, canvas_id)
    except ZeroUsersException:
        piechart = None

    return basic_stats, piechart


def checkbox_exercise(exercise, users, course_inst=None, revision=None):
    """
    Shows statistics on a single checkbox exercise.
    """

    answers = UserCheckboxExerciseAnswer.objects.filter(
        exercise=exercise, user__in=users, instance=course_inst
    )
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)
    chosen_answers = list(answers.values_list("chosen_answers", flat=True))
    chosen_answers_set = set(chosen_answers)
    answers_removed_count = 0
    answer_data = []
    choices = exercise.get_choices(exercise, revision)

    for answer in chosen_answers_set:
        try:
            choice = CheckboxExerciseAnswer.objects.get(id=answer)
        except CheckboxExerciseAnswer.DoesNotExist:
            answers_removed_count += chosen_answers.count(answer)
        else:
            latest = answers.filter(chosen_answers__id=answer).latest("answer_date").answer_date
            answer_data.append(
                (choice.answer, chosen_answers.count(answer), choice.correct, latest)
            )
    answer_data = sorted(answer_data, key=lambda x: x[1], reverse=True)

    return (course_inst, basic_stats, choices, piechart, answer_data, answers_removed_count)


def multiple_choice_exercise(exercise, users, course_inst=None, revision=None):
    """
    Shows statistics on a single multiple choice exercise.
    """

    answers = UserMultipleChoiceExerciseAnswer.objects.filter(
        exercise=exercise, user__in=users, instance=course_inst
    )
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)
    chosen_answers = list(answers.values_list("chosen_answer", flat=True))
    chosen_answers_set = set(chosen_answers)
    answers_removed_count = 0
    answer_data = []
    choices = exercise.get_choices(exercise, revision)

    for answer in chosen_answers_set:
        try:
            choice = MultipleChoiceExerciseAnswer.objects.get(id=answer)
        except MultipleChoiceExerciseAnswer.DoesNotExist:
            answers_removed_count += chosen_answers.count(answer)
        else:
            latest = answers.filter(chosen_answer=answer).latest("answer_date").answer_date
            answer_data.append(
                (choice.answer, chosen_answers.count(answer), choice.correct, latest)
            )
    answer_data = sorted(answer_data, key=lambda x: x[1], reverse=True)

    return (course_inst, basic_stats, choices, piechart, answer_data, answers_removed_count)


def textfield_exercise(exercise, users, course_inst=None, revision=None):
    """
    Shows statistics on a single textfield exercise.
    """

    answers = UserTextfieldExerciseAnswer.objects.filter(
        exercise=exercise, user__in=users, instance=course_inst
    )
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)
    given_answers = list(answers.values_list("given_answer", flat=True))
    given_answers_set = set(given_answers)

    answer_data = []
    incorrect_given = 0
    hinted_incorrect_given = 0
    incorrect_unique = 0
    hinted_incorrect_unique = 0
    choices = exercise.get_choices(exercise, revision)
    for answer in given_answers_set:
        count = given_answers.count(answer)
        correct, hinted, matches = textfield_eval(answer, choices)
        if not correct:
            incorrect_unique += 1
            incorrect_given += count
            if hinted:
                hinted_incorrect_unique += 1
                hinted_incorrect_given += count
        latest = answers.filter(given_answer=answer).latest("answer_date").answer_date
        answer_data.append((answer, count, correct, hinted, latest, matches))
    answer_data = sorted(answer_data, key=lambda x: x[1], reverse=True)

    try:
        hint_coverage_unique = hinted_incorrect_unique / incorrect_unique
    except ZeroDivisionError:
        hint_coverage_unique = 1.0

    try:
        hint_coverage_given = hinted_incorrect_given / incorrect_given
    except ZeroDivisionError:
        hint_coverage_given = 1.0

    return (
        course_inst,
        basic_stats,
        choices,
        piechart,
        answer_data,
        round(hint_coverage_unique * 100, 1),
        round(hint_coverage_given * 100, 1),
    )


def repeated_template_exercise(exercise, users, course_inst=None, revision=None):
    """
    Shows statistics on a single repeated template exercise.
    """
    answer_sessions = UserRepeatedTemplateExerciseAnswer.objects.filter(
        exercise=exercise, user__in=users, instance=course_inst
    )
    answer_instances = UserRepeatedTemplateInstanceAnswer.objects.filter(
        session_instance__in=answer_sessions.values_list("id", flat=True)
    )
    basic_stats, piechart = exercise_basic_answer_stats(
        exercise, users, answer_sessions, course_inst
    )

    correct_answers = answer_instances.filter(correct=True)

    answer_data = []
    for __ in correct_answers:
        answer_data.append(())

    hint_coverage_unique = 0.0
    hint_coverage_given = 0.0

    return (
        course_inst,
        basic_stats,
        piechart,
        answer_data,
        round(hint_coverage_unique * 100, 1),
        round(hint_coverage_given * 100, 1),
    )


def file_upload_exercise(exercise, users, course_inst=None, revision=None):
    """
    Shows statistics on a single file upload exercise.
    """

    answers = UserFileUploadExerciseAnswer.objects.filter(
        exercise=exercise, user__in=users, instance=course_inst
    )
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)

    return (course_inst, basic_stats, piechart)


def exercise_answer_stats(request, ctx, exercise, exercise_type_f, template):
    course_instances = course_instances_linked(exercise)

    stats = []
    users = []
    for course_inst in course_instances:
        # users_enrolled = filter_users_enrolled(all_users, course_inst)
        users_enrolled = course_inst.enrolled_users.get_queryset()  # until enroll implemented

        # this is not right, but we don't have knowledge of the parent page
        # in this context
        link = EmbeddedLink.objects.filter(instance=course_inst, embedded_page=exercise).first()

        stats.append(exercise_type_f(exercise, users_enrolled, course_inst, link.revision))
        users.extend(users_enrolled)

    stats.append(exercise_type_f(exercise, list(set(users))))
    ctx.update({"stats": stats})
    t = loader.get_template("stats/" + template)
    return HttpResponse(t.render(ctx, request))


def single_exercise(request, exercise):
    """
    Shows statistics on a single selected task.
    """
    if not (request.user.is_authenticated and request.user.is_active and request.user.is_staff):
        return HttpResponseForbidden("Only logged in admins can view exercise statistics!")

    tasktype = exercise.content_type

    ctx = {
        "content": exercise,
        "tasktype": exercise.get_human_readable_type(),
        "choices": exercise.get_choices(exercise),
    }

    if tasktype == "CHECKBOX_EXERCISE":
        return exercise_answer_stats(
            request, ctx, exercise, checkbox_exercise, "checkbox-stats.html"
        )
    if tasktype == "MULTIPLE_CHOICE_EXERCISE":
        return exercise_answer_stats(
            request, ctx, exercise, multiple_choice_exercise, "multiple-choice-stats.html"
        )
    if tasktype == "TEXTFIELD_EXERCISE":
        return exercise_answer_stats(
            request, ctx, exercise, textfield_exercise, "textfield-stats.html"
        )
    if tasktype == "FILE_UPLOAD_EXERCISE":
        return exercise_answer_stats(
            request, ctx, exercise, file_upload_exercise, "file-upload-stats.html"
        )
    if tasktype == "REPEATED_TEMPLATE_EXERCISE":
        return exercise_answer_stats(
            request, ctx, exercise, repeated_template_exercise, "repeated-template-stats.html"
        )

    return HttpResponseNotFound(f"No stats for exercise {exercise.slug} found!")


def user_task(request, user_name, task_name):
    """Shows a user's answers to a task."""
    if not request.user.is_authenticated and not request.user.is_staff:
        return HttpResponseNotFound()

    content = ContentPage.objects.get(slug=task_name)

    tasktype = content.content_type

    ruser = User.objects.get(username=user_name)

    checkboxanswers = multichoiceanswers = textfieldanswers = fileanswers = None
    if tasktype == "CHECKBOX_EXERCISE":
        checkboxanswers = UserCheckboxExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
        multichoiceanswers = UserMultipleChoiceExerciseAnswer.objects.filter(
            exercise=content, user=ruser
        )
    elif tasktype == "TEXTFIELD_EXERCISE":
        textfieldanswers = UserTextfieldExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "FILE_UPLOAD_EXERCISE":
        fileanswers = UserFileUploadExerciseAnswer.objects.filter(exercise=content, user=ruser)

    t = loader.get_template("stats/user-task-stats.html")
    c = {
        "username": user_name,
        "taskname": task_name,
        "checkboxanswers": checkboxanswers,
        "multichoiceanswers": multichoiceanswers,
        "textfieldanswers": textfieldanswers,
        "fileanswers": fileanswers,
    }
    return HttpResponse(t.render(c, request))


def all_exercises(request, course_name):
    """Shows statistics for all the tasks."""
    if not request.user.is_authenticated and not request.user.is_staff:
        return HttpResponseNotFound()

    tasks = ContentPage.objects.all()
    staff = User.objects.filter(is_staff=True)

    task_infos = []
    for task in tasks:
        taskname = task.name
        taskurl = "/" + course_name + "/" + task.slug

        tasktype = task.content_type

        if tasktype == "CHECKBOX_EXERCISE":
            all_evaluations = Evaluation.objects.filter(
                useranswer__usercheckboxexerciseanswer__exercise=task
            ).exclude(useranswer__user__in=staff)
        elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
            all_evaluations = Evaluation.objects.filter(
                useranswer__usermultiplechoiceexerciseanswer__exercise=task
            ).exclude(useranswer__user__in=staff)
        elif tasktype == "TEXTFIELD_EXERCISE":
            all_evaluations = Evaluation.objects.filter(
                useranswer__usertextfieldexerciseanswer__exercise=task
            ).exclude(useranswer__user__in=staff)
        elif tasktype == "FILE_UPLOAD_EXERCISE":
            all_evaluations = Evaluation.objects.filter(
                useranswer__userfileuploadexerciseanswer__exercise=task
            ).exclude(useranswer__user__in=staff)
        else:
            continue

        total_attempts = all_evaluations.count()
        by_users = all_evaluations.values_list("useranswer__user", flat=True)
        unique_users_set = set(list(by_users))
        unique_users = len(unique_users_set)
        correct = all_evaluations.filter(points__gt=0.0).values_list("useranswer__user", flat=True)
        correct_set = set(list(correct))
        correct_by = len(correct_set)
        try:
            avg = 1.0 * total_attempts / unique_users
        except ZeroDivisionError:
            avg = "N/A"

        task_infos.append((taskname, taskurl, total_attempts, unique_users, correct_by, avg))

    t = loader.get_template("stats/alltaskstats.html")
    c = {
        "course_name": course_name,
        "task_infos": task_infos,
    }
    return HttpResponse(t.render(c, request))


def course_users(request, course_slug, content_to_search, year, month, day):
    """
    Admin view that shows a table of all users and the tasks they've done on a particular course.
    """
    if (
        not request.user.is_authenticated
        and not request.user.is_active
        and not request.user.is_staff
    ):
        return HttpResponseNotFound()

    users = User.objects.all()
    # content_nodes = selected_course.contents.all()
    # contents = [cn.content for cn in content_nodes]

    cns = ContentPage.objects.get(slug=content_to_search).content.splitlines()
    content_names = []
    for line in cns:
        mo = re.match(r"^\[\[\[(?P<embname>.+)\]\]\]", line)
        if mo:
            content_names.append(mo.group("embname"))
    deadline = datetime.datetime(int(year), int(month), int(day))
    contents = ContentPage.objects.filter(slug__in=content_names)

    user_evaluations = []
    for user in users:
        username = user.userprofile.student_id or user.username
        if not deadline:
            db_user_evaluations = Evaluation.objects.filter(useranswer__user=user, points__gt=0.0)
        else:
            db_user_evaluations = Evaluation.objects.filter(
                useranswer__user=user, points__gt=0.0, useranswer__answer_date__lt=deadline
            )
        evaluations = []

        for content in contents:
            exercise = content.get_type_object()
            tasktype = content.content_type
            if tasktype == "CHECKBOX_EXERCISE":
                db_evaluations = db_user_evaluations.filter(
                    useranswer__usercheckboxexerciseanswer__exercise=content
                )
            elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
                db_evaluations = db_user_evaluations.filter(
                    useranswer__usermultiplechoiceexerciseanswer__exercise=content
                )
            elif tasktype == "TEXTFIELD_EXERCISE":
                db_evaluations = db_user_evaluations.filter(
                    useranswer__usertextfieldexerciseanswer__exercise=content
                )
            elif tasktype == "FILE_UPLOAD_EXERCISE":
                db_evaluations = db_user_evaluations.filter(
                    useranswer__userfileuploadexerciseanswer__exercise=content
                )
            else:
                db_evaluations = []

            if db_evaluations:
                evaluations.append(1)
            else:
                evaluations.append(0)
        user_evaluations.append((username, evaluations, sum(evaluations)))

    t = loader.get_template("stats/usertable.html")
    c = {
        "course_slug": course_slug,
        "content_count": len(contents),
        "contents": contents,
        "user_evaluations": user_evaluations,
    }
    return HttpResponse(t.render(c, request))


def users_all(request):
    if not (request.user.is_authenticated and request.user.is_active and request.user.is_staff):
        return HttpResponseNotFound()

    users = User.objects.all().order_by("username")
    exercises = ContentPage.objects.all().exclude(content_type="LECTURE").order_by("name")

    # Argh...
    table_rows = [
        [user] + [exercise.get_type_object().get_user_evaluation(user) for exercise in exercises]
        for user in users
    ]

    t = loader.get_template("stats/users-all.html")
    c = {
        "users": users,
        "exercises": exercises,
        "table_rows": table_rows,
    }
    return HttpResponse(t.render(c, request))


def color_generator(total_colors):
    saturation = 0.35
    value = 1.0
    for hue in range(0, 360, int(360 / total_colors)):
        r, g, b = [255 * result for result in colorsys.hsv_to_rgb(hue / 360, saturation, value)]
        yield f"rgba({r:.0f},{g:.0f},{b:.0f},0.65)"


def users_course(request, course_slug, instance_slug):
    if not (request.user.is_authenticated and request.user.is_active and request.user.is_staff):
        return HttpResponseNotFound()

    users = User.objects.all().order_by("username")
    course = Course.objects.get(slug=course_slug)
    instance = CourseInstance.objects.get(slug=instance_slug, course=course)

    exercises = course_exercises_with_color(course, instance)

    # Argh...
    table_rows = [
        [user] + [(user_evaluation(user, e[1]), e[1].default_points) for e in exercises]
        for user in users
    ]

    t = loader.get_template("stats/users-course.html")
    c = {
        "course": course,
        "users": users,
        "exercises": exercises,
        "table_rows": table_rows,
    }
    return HttpResponse(t.render(c, request))


class ZeroUsersException(Exception):
    pass


# ^
# |
# OLD STUFF
# NEW STUFF
# |
# v


@ensure_responsible
def instance_console(request, course, instance):
    task_meta = cache.get(f"{instance.slug}_stat_meta")
    task_meta = task_meta and json.loads(task_meta)
    if task_meta and task_meta["completed"]:
        gen_timestamp = task_meta["completed"]
        stat_status = _("Last generated: {gen_timestamp}").format(
            gen_timestamp=task_meta["completed"]
        )
    elif task_meta:
        gen_timestamp = None
        stat_status = _("Generation of new stats has been requested.")
    else:
        gen_timestamp = None
        stat_status = _("Stats have not been generated.")

    task_summary = TaskSummary.objects.filter(instance=instance)

    t = loader.get_template("stats/instance-console.html")
    c = {
        "course": course,
        "instance": instance,
        "stat_status": stat_status,
        "task_summary": task_summary,
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def generate_instance_stats(request, course, instance):
    task_meta = cache.get(f"{instance.slug}_stat_meta")
    task_meta = task_meta and json.loads(task_meta)
    if task_meta and task_meta["completed"] is None:
        task = celery_app.AsyncResult(id=task_meta["task_id"])
        if task.state in ("PENDING", "STARTED"):
            return HttpResponse(
                _("Stats generation for '{instance}' has already been requested.").format(
                    instance=instance.name
                ),
                status=409,
            )

    data = {"msg": _("Stats requested. Request processing starts approximately:")}
    if settings.STAT_GENERATION_HOUR is None:
        task = chain(
            stat_tasks.generate_instance_user_stats.si(instance_slug=instance.slug),
            stat_tasks.generate_instance_tasks_summary.si(instance_slug=instance.slug),
            stat_tasks.finalize_instance_stats.s(instance_slug=instance.slug),
        ).apply_async(ignore_result=True)
        data["eta"] = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    else:
        today = datetime.datetime.today()
        eta = today.replace(hour=settings.STAT_GENERATION_HOUR, minute=0, second=0)
        task = chain(
            stat_tasks.generate_instance_user_stats.si(instance_slug=instance.slug),
            stat_tasks.generate_instance_tasks_summary.si(instance_slug=instance.slug),
            stat_tasks.finalize_instance_stats.s(instance_slug=instance.slug),
        ).apply_async(eta=eta, ignore_result=True)
        data["eta"] = eta.strftime("%Y-%m-%d %H:%M:%S")

    cache.set(
        f"{instance.slug}_stat_meta",
        json.dumps({"task_id": task.task_id, "completed": None}),
    )
    return JsonResponse(data)
