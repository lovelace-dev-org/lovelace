import re

import django
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.template import Context, RequestContext, loader
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.utils import timezone
from django.utils.safestring import mark_safe

from courses.models import *

# TODO: A view that displays statistics of a page that has embedded pages.
#       E.g. the average completion status, how many of total course
#       participants have done how much etc.
#       - links to the stats of individual exercises
#           * sorting by completion rate
#           * sorting by total tries, average tries before correct etc.

def textfield_eval(given, answers):
    given = given.replace("\r\n", "\n").replace("\n\r", "\n")
    correct = True
    hinted = False
    errors = []
    for answer in answers:
        if answer.regexp:
            try:
                if re.match(answer.answer, given) and answer.correct and correct == True:
                    correct = True
                    break
                elif re.match(answer.answer, given) and not answer.correct:
                    correct = False
                    if answer.hint: hinted = True
                elif not re.match(answer.answer, given) and answer.correct:
                    correct = False
            except re.error as e_msg:
                errors.append("Regexp error: " + e_msg)
                correct = False
        else:
            if given == answer.answer and answer.correct and correct == True:
                correct = True
                break
            elif given == answer.answer and not answer.correct:
                correct = False
                if answer.hint: hinted = True
            elif given != answer.answer and answer.correct:
                correct = False
    return (correct, hinted)

def single_task(request, task_name):
    '''Shows statistics on the selected task.'''
    if not request.user.is_authenticated() and not request.user.is_active and not request.user.is_staff:
        return HttpResponseNotFound()

    checkbox_answers = radiobutton_answers = textfield_answers = file_answers = None
    textfield_answers_count = textfield_final = textfield_user_count = None
    file_answers = file_answers_count = file_user_count = file_correctly_by = None
    radiobutton_answers_count = radiobutton_final = None
    content_page = ContentPage.objects.get(slug=task_name)
    
    exercise = content_page.get_type_object()
    tasktype = content_page.content_type
    question = content_page.question
    choices = answers = exercise.get_choices()

    if tasktype == "CHECKBOX_EXERCISE":
        checkbox_answers = UserCheckboxExerciseAnswer.objects.filter(exercise=content_page)
    elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
        radiobutton_answers = UserMultipleChoiceExerciseAnswer.objects.filter(exercise=content_page)
        radiobutton_answers_count = radiobutton_answers.count()
        radiobutton_selected_answers = list(radiobutton_answers.values_list("chosen_answer", flat=True))
        radiobutton_set = set(radiobutton_selected_answers)
        radiobutton_final = []
        for answer in radiobutton_set:
            answer_choice = RadiobuttonExerciseAnswer.objects.get(id=answer)
            radiobutton_final.append((answer_choice.answer, radiobutton_selected_answers.count(answer), answer_choice.correct))
    elif tasktype == "TEXTFIELD_EXERCISE":
        textfield_answers1 = UserTextfieldExerciseAnswer.objects.filter(exercise=content_page)
        textfield_answers = list(textfield_answers1.values_list("given_answer", flat=True))
        textfield_answers_count = len(textfield_answers)
        textfield_set = set(textfield_answers)

        textfield_user_count = len(set(list(textfield_answers1.values_list("user", flat=True))))
        textfield_final = []
        for answer in textfield_set:
            latest = textfield_answers1.filter(given_answer=answer).latest('answer_date').answer_date
            textfield_final.append((answer, textfield_answers.count(answer),) + textfield_eval(answer, answers) + (latest,))
        textfield_final = sorted(textfield_final, key=lambda x: x[1], reverse=True)
    elif tasktype == "FILE_UPLOAD_EXERCISE":
        file_answers = list(UserFileExerciseAnswer.objects.filter(exercise=content_page).values_list("user", flat=True))
        file_answers_count = len(file_answers) # how many times answered
        file_set = set(file_answers)
        file_user_count = len(file_set) # how many different users have answered
        file_correctly_by = 0
        for user in file_set:
            evaluations = Evaluation.objects.filter(useranswer__userfileexerciseanswer__exercise=content_page, useranswer__user=user)
            correct = evaluations.filter(points__gt=0.0)
            if correct: file_correctly_by += 1

    t = loader.get_template("stats/task_stats.html")
    c = RequestContext(request, {
        "content": content_page,
        "question": question,
        "tasktype": tasktype,
        "choices": choices,
        "answers": answers,
        "checkbox_answers": checkbox_answers,

        "radiobutton_answers": radiobutton_answers,
        "radiobutton_answers_count": radiobutton_answers_count,
        "radiobutton_final": radiobutton_final,

        "textfield_answers": textfield_answers,
        "textfield_answers_count": textfield_answers_count,
        "textfield_final": textfield_final,
        "textfield_user_count": textfield_user_count,

        "file_answers": file_answers,
        "file_answers_count": file_answers_count,
        "file_user_count": file_user_count,
        "file_correctly_by": file_correctly_by,
    })
    return HttpResponse(t.render(c))

def user_task(request, user_name, task_name):
    '''Shows a user's answers to a task.'''
    if not request.user.is_authenticated() and not request.user.is_staff:
        return HttpResponseNotFound()

    content = ContentPage.objects.get(slug=task_name)

    exercise = content_page.get_type_object()
    tasktype = content_page.content_type
    question = content.question
    choices = answers = exercise.get_choices()

    ruser = User.objects.get(username=user_name)

    checkboxanswers = radiobuttonanswers = textfieldanswers = fileanswers = None
    if tasktype == "CHECKBOX_EXERCISE":
        checkboxanswers = UserCheckboxExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "MULTIPLE_CHOICE_EXERCISE":
        radiobuttonanswers = UserRadiobuttonExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "TEXTFIELD_EXERCISE":
        textfieldanswers = UserTextfieldExerciseAnswer.objects.filter(exercise=content, user=ruser)
    elif tasktype == "FILE_UPLOAD_EXERCISE":
        fileanswers = UserFileExerciseAnswer.objects.filter(exercise=content, user=ruser)

    t = loader.get_template("stats/user_task_stats.html")
    c = RequestContext(request, {
        'username': user_name,
        'taskname': task_name,
        'checkboxanswers': checkboxanswers,
        'radiobuttonanswers': radiobuttonanswers,
        'textfieldanswers': textfieldanswers,
        'fileanswers': fileanswers,
    })
    return HttpResponse(t.render(c))

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
    c = RequestContext(request, {
        'course_name': course_name,
        'task_infos': task_infos,
    })
    return HttpResponse(t.render(c))

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
    c = RequestContext(request, {
        'course_slug':course_slug,
        'content_count':len(contents),
        'contents':contents,
        'user_evaluations':user_evaluations,
    })
    return HttpResponse(t.render(c))

def users_all(request):
    if not (request.user.is_authenticated() and request.user.is_active and\
       request.user.is_staff):
        return HttpResponseNotFound()

    users = User.objects.all().order_by('username')
    exercises = ContentPage.objects.all().exclude(content_type='LECTURE')\
                                         .order_by('name')

    # Argh...
    table_rows = [
        [user.username] +
        [exercise.get_type_object().get_user_evaluation(user) for exercise in exercises]
        for user in users
    ]

    t = loader.get_template("stats/users-all.html")
    c = RequestContext(request, {
        'users': users,
        'exercises': exercises,
        'table_rows': table_rows,
    })
    return HttpResponse(t.render(c))

