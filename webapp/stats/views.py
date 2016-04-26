import re
import math
import statistics

import django
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.template import loader
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from courses.models import *

# TODO: A view that displays statistics of a page that has embedded pages.
#       E.g. the average completion status, how many of total course
#       participants have done how much etc.
#       - links to the stats of individual exercises
#           * sorting by completion rate
#           * sorting by total tries, average tries before correct etc.

###########################################################
# Some helper functions which won't be needed after the course enrollment of 
# users and the course instances have been implemented.


NO_USERS_MSG = "No users to calculate!"

def user_evaluation(user, exercise):
    return exercise.get_type_object().get_user_evaluation(user)

def user_has_answered(user, exercise):
    return user_evaluation(user, exercise) != "unanswered"

def course_exercises_with_color(course):
    exercises = []
    parent_pages = course.contents.select_related('content').order_by('ordinal_number')
    cg = color_generator(parent_pages.count())
    
    for p in parent_pages:
        color = next(cg)
        if p.content.embedded_pages.count() > 0:
            all_pages = list(p.content.embedded_pages.all().order_by('emb_embedded__ordinal_number'))
            exercises.extend(list(zip(itertools.cycle([color]), all_pages)))
    return exercises

def course_exercises(course):
    exercises = []

    # TODO: course has no contents, use instance
    parent_pages = course.contents.select_related('content').order_by('ordinal_number')
    
    for p in parent_pages:
        if p.content.embedded_pages.count() > 0:
            all_pages = list(p.content.embedded_pages.all().order_by('emb_embedded__ordinal_number'))
            exercises.extend(all_pages)
    return exercises

def filter_users_on_course(users, course):
    return users

def courses_linked(exercise):
    linked = []
    courses = Course.objects.all()
    
    for course in courses:
        if exercise in course_exercises(course):
            linked.append(course)
    return linked

########################################################### 

def textfield_eval(given, answers):
    given_answer = given.replace("\r", "")
    correct = False
    hinted = False
    commented = False
    matches = []

    re_validate = lambda db_ans, given_ans: re.match(db_ans, given_ans) is not None
    str_validate = lambda db_ans, given_ans: db_ans == given_ans
    
    for answer in answers:
        validate = re_validate if answer.regexp else str_validate
        
        try:
            match = validate(answer.answer, given_answer)
        except re.error as e:
            matches.append((answer.answer, "{}".format(e)))
            correct = False
            continue

        if match and answer.correct:
            correct = True
            matches.append((answer.answer, ""))
            if answer.comment:
                commented = True
        elif match and not answer.correct:
            matches.append((answer.answer, ""))
            if answer.hint:
                hinted = True
            if answer.comment:
                commented = True
                    
    return (correct, hinted, matches)

def answers_average(answer_count, user_count):
    """
    Calculates the average of the number of answers per user.
    """

    try:
        return round(answer_count / user_count, 2)
    except ZeroDivisionError:
        raise ZeroUsersException("No users to calculate average answer count!") 

def answers_standard_distrib(user_count, answers_avg, answer_counts):
    """
    Calculates the standard distribution of the number of answers per user.
    """
    
    deviations_squared = ((ac - answers_avg) ** 2 for ac in answer_counts)
    try:
        variance = (1 / user_count) * sum(deviations_squared)
    except ZeroDivisionError:
        raise ZeroUsersException("No users to calculate standard deviation!")
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
    except ZeroDivisionError:
        raise ZeroUsersException("No users to create piechart!") 
    correct_deg = round(correct_pct * 360)
    incorrect_deg = round(incorrect_pct * 360)
    not_answered_deg = 360 - correct_deg - incorrect_deg

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

def checkbox_exercise(exercise, users, course_inst=None):
    """
    Shows statistics on a single checkbox exercise.
    """
    
    answers = UserCheckboxExerciseAnswer.objects.filter(exercise=exercise, user__in=users)
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)
    chosen_answers = list(answers.values_list("chosen_answers", flat=True))
    chosen_answers_set = set(chosen_answers)
    answers_removed_count = 0    
    answer_data = []

    for answer in chosen_answers_set:
        try:
            choice = CheckboxExerciseAnswer.objects.get(id=answer)
        except CheckboxExerciseAnswer.DoesNotExist:
            answers_removed_count += chosen_answers.count(answer)
        else:
            latest = answers.filter(chosen_answers__id=answer).latest('answer_date').answer_date
            answer_data.append((choice.answer, chosen_answers.count(answer), choice.correct, latest))
    answer_data = sorted(answer_data, key=lambda x: x[1], reverse=True)
    
    return (course_inst,
            basic_stats,
            piechart,
            answer_data, 
            answers_removed_count)

def multiple_choice_exercise(exercise, users, course_inst=None):
    """
    Shows statistics on a single multiple choice exercise.
    """
    
    answers = UserMultipleChoiceExerciseAnswer.objects.filter(exercise=exercise, user__in=users)
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)
    chosen_answers = list(answers.values_list("chosen_answer", flat=True))
    chosen_answers_set = set(chosen_answers)
    answers_removed_count = 0
    answer_data = []

    for answer in chosen_answers_set:
        try:
            choice = MultipleChoiceExerciseAnswer.objects.get(id=answer)
        except MultipleChoiceExerciseAnswer.DoesNotExist:
            answers_removed_count += chosen_answers.count(answer)
        else:
            latest = answers.filter(chosen_answer=answer).latest('answer_date').answer_date
            answer_data.append((choice.answer, chosen_answers.count(answer), choice.correct, latest))
    answer_data = sorted(answer_data, key=lambda x: x[1], reverse=True)
            
    return (course_inst,
            basic_stats,
            piechart,
            answer_data, 
            answers_removed_count)

def textfield_exercise(exercise, users, course_inst=None):
    """
    Shows statistics on a single textfield exercise.
    """

    answers = UserTextfieldExerciseAnswer.objects.filter(exercise=exercise, user__in=users)
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)
    given_answers = list(answers.values_list("given_answer", flat=True))
    given_answers_set = set(given_answers)

    answer_data = []
    incorrect_given = 0
    hinted_incorrect_given = 0
    incorrect_unique = 0
    hinted_incorrect_unique = 0
    choices = exercise.get_type_object().get_choices()
    for answer in given_answers_set:
        count = given_answers.count(answer)
        correct, hinted, matches = textfield_eval(answer, choices)
        if not correct:
            incorrect_unique += 1
            incorrect_given += count
            if hinted:
                hinted_incorrect_unique += 1
                hinted_incorrect_given += count
        latest = answers.filter(given_answer=answer).latest('answer_date').answer_date
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

    return (course_inst,
            basic_stats,
            piechart,
            answer_data, 
            round(hint_coverage_unique * 100, 1),
            round(hint_coverage_given * 100, 1))
    
def file_upload_exercise(exercise, users, course_inst=None):
    """
    Shows statistics on a single file upload exercise.
    """

    answers = UserFileUploadExerciseAnswer.objects.filter(exercise=exercise, user__in=users)
    basic_stats, piechart = exercise_basic_answer_stats(exercise, users, answers, course_inst)
    
    return (course_inst,
            basic_stats,
            piechart)

def exercise_answer_stats(request, ctx, exercise, exercise_type_f, template):
    all_users = User.objects.filter(is_staff=False).order_by('username')
    courses = courses_linked(exercise)

    stats = []
    users = []
    for course in courses:
        users_on_course = filter_users_on_course(all_users, course)
        stats.append(exercise_type_f(exercise, users_on_course, course))
        users.extend(users_on_course)

    stats.append(exercise_type_f(exercise, list(set(users))))
    ctx.update({"stats": stats})
    t = loader.get_template("stats/" + template)
    return HttpResponse(t.render(ctx, request))
    
def single_exercise(request, content_slug):
    """
    Shows statistics on a single selected task.
    """
    if not request.user.is_authenticated() and not request.user.is_active and not request.user.is_staff:
        return HttpResponseNotFound()

    try:
        exercise = ContentPage.objects.get(slug=content_slug)
    except ContentPage.DoesNotExist:
        return HttpResponseNotFound("No exercise {} found!".format(content_slug))
    tasktype = exercise.content_type

    tasktype_verbose = "unknown"
    for choice, verbose in ContentPage.CONTENT_TYPE_CHOICES:
        if choice == tasktype:
            tasktype_verbose = verbose.lower()
            break

    ctx = {
        "content": exercise,
        "tasktype": tasktype_verbose,
        "choices": exercise.get_choices(exercise),
    }

    if tasktype == "CHECKBOX_EXERCISE":
        return exercise_answer_stats(request, ctx, exercise, checkbox_exercise, "checkbox_stats.html")
    elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
        return exercise_answer_stats(request, ctx, exercise, multiple_choice_exercise, "multiple_choice_stats.html")
    elif tasktype == "TEXTFIELD_EXERCISE":
        return exercise_answer_stats(request, ctx, exercise, textfield_exercise, "textfield_stats.html")
    elif tasktype == "FILE_UPLOAD_EXERCISE":
        return exercise_answer_stats(request, ctx, exercise, file_upload_exercise, "file_upload_stats.html")
    else:
        return HttpResponseNotFound("No stats for exercise {} found!".format(content_slug))

def user_task(request, user_name, task_name):
    '''Shows a user's answers to a task.'''
    if not request.user.is_authenticated() and not request.user.is_staff:
        return HttpResponseNotFound()

    content = ContentPage.objects.get(slug=task_name)

    exercise = content_page # content_page.get_type_object()
    tasktype = content_page.content_type
    question = content.question
    choices = answers = exercise.get_choices(exercise) 

    ruser = User.objects.get(username=user_name)

    checkboxanswers = multichoiceanswers = textfieldanswers = fileanswers = None
    if tasktype == "CHECKBOX_EXERCISE":
        checkboxanswers = UserCheckboxExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
        multichoiceanswers = UserMultipleChoiceExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "TEXTFIELD_EXERCISE":
        textfieldanswers = UserTextfieldExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "FILE_UPLOAD_EXERCISE":
        fileanswers = UserFileUploadExerciseAnswer.objects.filter(exercise=content, user=ruser)

    t = loader.get_template("stats/user_task_stats.html")
    c = {
        'username': user_name,
        'taskname': task_name,
        'checkboxanswers': checkboxanswers,
        'multichoiceanswers': multichoiceanswers,
        'textfieldanswers': textfieldanswers,
        'fileanswers': fileanswers,
    }
    return HttpResponse(t.render(c, request))

def all_exercises(request, course_name):
    '''Shows statistics for all the tasks.'''
    if not request.user.is_authenticated() and not request.user.is_staff:
        return HttpResponseNotFound()

    tasks = ContentPage.objects.all()
    staff = User.objects.filter(is_staff=True)
    non_staff = User.objects.filter(is_staff=False)

    task_infos = []
    for task in tasks:
        taskname = task.name
        taskurl = "/" + course_name + "/" + task.slug
        
        exercise = task.get_type_object()
        tasktype = task.content_type
        question = task.question
        choices = answers = exercise.get_choices()

        if tasktype == "CHECKBOX_EXERCISE":
            all_evaluations = Evaluation.objects.filter(useranswer__usercheckboxexerciseanswer__exercise=task).exclude(useranswer__user__in=staff)
        elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
            all_evaluations = Evaluation.objects.filter(useranswer__usermultiplechoiceexerciseanswer__exercise=task).exclude(useranswer__user__in=staff)
        elif tasktype == "TEXTFIELD_EXERCISE":
            all_evaluations = Evaluation.objects.filter(useranswer__usertextfieldexerciseanswer__exercise=task).exclude(useranswer__user__in=staff)
        elif tasktype == "FILE_UPLOAD_EXERCISE":
            all_evaluations = Evaluation.objects.filter(useranswer__userfileuploadexerciseanswer__exercise=task).exclude(useranswer__user__in=staff)
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
            avg = 1.0*total_attempts/unique_users
        except ZeroDivisionError:
            avg = "N/A"

        task_infos.append((taskname, taskurl, total_attempts, unique_users, correct_by, avg))

    t = loader.get_template("stats/alltaskstats.html")
    c = {
        'course_name': course_name,
        'task_infos': task_infos,
    }
    return HttpResponse(t.render(c, request))

def course_users(request, course_slug, content_to_search, year, month, day):
    '''Admin view that shows a table of all users and the tasks they've done on a particular course.'''
    if not request.user.is_authenticated() and not request.user.is_active and not request.user.is_staff:
        return HttpResponseNotFound()

    selected_course = Training.objects.get(name=course_slug)
    users = User.objects.all()
    #content_nodes = selected_course.contents.all()
    #contents = [cn.content for cn in content_nodes]

    cns = ContentPage.objects.get(slug=content_to_search).content.splitlines()
    content_names = []
    for line in cns:
        mo = re.match("^\[\[\[(?P<embname>.+)\]\]\]", line)
        if mo:
            content_names.append(mo.group("embname"))
    deadline = datetime.datetime(int(year), int(month), int(day))
    contents = ContentPage.objects.filter(slug__in=content_names)
    print(content_names)

    user_evaluations = []
    for user in users:
        username = user.userprofile.student_id or user.username
        if not deadline: db_user_evaluations = Evaluation.objects.filter(useranswer__user=user, points__gt=0.0)
        else: db_user_evaluations = Evaluation.objects.filter(useranswer__user=user, points__gt=0.0, useranswer__answer_date__lt=deadline)
        evaluations = []

        print(username,)

        for content in contents:
            exercise = content.get_type_object()
            tasktype = content.content_type
            question = content.question
            choices = answers = exercise.get_choices()
            if tasktype == "CHECKBOX_EXERCISE":
                db_evaluations = db_user_evaluations.filter(useranswer__usercheckboxexerciseanswer__exercise=content)
            elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
                db_evaluations = db_user_evaluations.filter(useranswer__usermultiplechoiceexerciseanswer__exercise=content)
            elif tasktype == "TEXTFIELD_EXERCISE":
                db_evaluations = db_user_evaluations.filter(useranswer__usertextfieldexerciseanswer__exercise=content)
            elif tasktype == "FILE_UPLOAD_EXERCISE":
                db_evaluations = db_user_evaluations.filter(useranswer__userfileuploadexerciseanswer__exercise=content)
            else:
                db_evaluations = []

            if db_evaluations:
                evaluations.append(1)
            else:
                evaluations.append(0)
        user_evaluations.append((username, evaluations, sum(evaluations)))

    t = loader.get_template("stats/usertable.html")
    c = {
        'course_slug':course_slug,
        'content_count':len(contents),
        'contents':contents,
        'user_evaluations':user_evaluations,
    }
    return HttpResponse(t.render(c, request))

def users_all(request):
    if not (request.user.is_authenticated() and request.user.is_active and\
       request.user.is_staff):
        return HttpResponseNotFound()

    users = User.objects.all().order_by('username')
    exercises = ContentPage.objects.all().exclude(content_type='LECTURE')\
                                         .order_by('name')

    # Argh...
    table_rows = [
        [user] +
        [exercise.get_type_object().get_user_evaluation(user) for exercise in exercises]
        for user in users
    ]

    t = loader.get_template("stats/users-all.html")
    c = {
        'users': users,
        'exercises': exercises,
        'table_rows': table_rows,
    }
    return HttpResponse(t.render(c, request))

def color_generator(total_colors):
    import colorsys
    saturation = 0.35
    value = 1.0
    for hue in range(0, 360, int(360/total_colors)):
        r, g, b = [255 * result for result in colorsys.hsv_to_rgb(hue/360, saturation, value)]
        #yield '#{:x}{:x}{:x}'.format(int(r), int(g), int(b))
        yield 'rgba({},{},{},0.65)'.format(int(r), int(g), int(b))

def users_course(request, course):
    if not (request.user.is_authenticated() and request.user.is_active and\
            request.user.is_staff):
        return HttpResponseNotFound()

    users = User.objects.all().order_by('username')
    course = Course.objects.get(slug=course)

    exercises = course_exercises_with_color(course)
    
    # Argh...
    table_rows = [
        [user] +
        [user_evaluation(user, e[1]) for e in exercises]
        for user in users
    ]

    t = loader.get_template("stats/users-course.html")
    c = {
        'course': course,
        'users': users,
        'exercises': exercises,
        'table_rows': table_rows,
    }
    return HttpResponse(t.render(c, request))

class ZeroUsersException(Exception):
    pass
