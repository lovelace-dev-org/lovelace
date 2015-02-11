"""
Django views for rendering the course contents and checking exercises.
"""
import datetime
import json
from cgi import escape

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect,\
    HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed,\
    HttpResponseServerError
from django.template import Context, RequestContext, Template, loader
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from celery.result import AsyncResult

from courses.models import *
from courses.forms import *

import courses.markupparser as markupparser
import courses.blockparser as blockparser

def index(request):
    course_list = Course.objects.all()

    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course_list': course_list,
    })
    return HttpResponse(t.render(c))
 
def course(request, course_slug):
    course = Course.objects.get(slug=course_slug)

    frontpage = course.frontpage
    if frontpage:
        content_slug = frontpage.slug
        context = content(request, course_slug, content_slug, frontpage=True)
    else:
        context = {}

    context["course"] = course 

    contents = course.contents.all().order_by('parentnode', '-id')
    if len(contents) > 0:
        tree = []    
        tree.append((mark_safe('>'), None))
        for content_ in contents:
            course_tree(tree, content_, request.user)
        tree.append((mark_safe('<'), None))
        context["content_tree"] = tree

    t = loader.get_template("courses/course.html")
    c = RequestContext(request, context)
    return HttpResponse(t.render(c))

def course_tree(tree, node, user):
    evaluation = "unanswered"
    if user.is_authenticated():
        exercise = node.content.get_type_object()
        evaluation = exercise.get_user_evaluation(user)

    list_item = (node.content, evaluation)
    if list_item not in tree:
        tree.append(list_item)

    children = ContentGraph.objects.filter(parentnode=node)
    if len(children) > 0:
        tree.append((mark_safe('>'), None))
        for child in children:
            course_tree(tree, child, user)
        tree.append((mark_safe('<'), None))

def check_answer(request, course_slug, content_slug):
    """
    Saves and evaluates a user's answer to an exercise and sends the results
    back to the user.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])

    if not request.user.is_active:
        return HttpResponse("You have not logged in.")

    course = Course.objects.get(slug=course_slug)
    content = ContentPage.objects.get(slug=content_slug)
    # TODO: Ensure that the content really belongs to the course

    # Check if a deadline exists and if it has already passed
    try:
        content_graph = course.contents.get(content=content)
    except ContentGraph.DoesNotExist as e:
        pass
    else:
        if not content_graph.deadline or datetime.datetime.now() < content_graph.deadline:
            pass
        else:
            # TODO: Use a template!
            return HttpResponse("The deadline for this exercise (%s) has passed. Your answer will not be evaluated!" % (content_graph.deadline))

    user = request.user
    ip = request.META.get('REMOTE_ADDR')
    answer = request.POST
    files = request.FILES

    exercise = content.get_type_object()
    
    answer_object = exercise.save_answer(user, ip, answer, files)
    evaluation = exercise.check_answer(user, ip, answer, files, answer_object)
    if not exercise.manually_evaluated:
        if exercise.content_type == "FILE_UPLOAD_EXERCISE":
            task_id = evaluation["task_id"]
            return HttpResponseRedirect(reverse('courses:check_progress',
                                                kwargs={"course_slug": course_slug,
                                                        "content_slug": content_slug,
                                                        "task_id": task_id}))
        exercise.save_evaluation(user, evaluation, answer_object)
        evaluation["manual"] = False
    else:
        evaluation["manual"] = True

    # TODO: Replace with JSON
    t = loader.get_template("courses/exercise_evaluation.html")
    c = Context(evaluation)
    return HttpResponse(t.render(c))

def check_progress(request, course_slug, content_slug, task_id):
    # Based on https://djangosnippets.org/snippets/2898/
    # TODO: Check permissions
    task = AsyncResult(task_id)
    if task.ready():
        return HttpResponseRedirect(reverse('courses:file_exercise_evaluation',
                                            kwargs={"course_slug": course_slug,
                                                    "content_slug": content_slug,
                                                    "task_id": task_id,}))
    else:
        data = {"state": task.state, "metadata": task.info}
        return JsonResponse(data)

def file_exercise_evaluation(request, course_slug, content_slug, task_id):
    # TODO: Render the exercise results and send them to the user
    t = loader.get_template("courses/file_exercise_evaluation.html")
    c = Context({
        'placeholder': 'placeholder',
    })
    return HttpResponse(t.render(c))

def content(request, course_slug, content_slug, **kwargs):
    course = Course.objects.get(slug=course_slug)
    # TODO: Ensure content is part of course!
    content = ContentPage.objects.get(slug=content_slug).get_type_object()

    content_graph = None
    try:
        content_graph = course.contents.get(content=content)
    except ContentGraph.DoesNotExist as e:
        pass

    content_type = content.content_type
    question = blockparser.parseblock(escape(content.question))
    choices = answers = content.get_choices()

    evaluation = None
    if request.user.is_authenticated():
        if not content_graph or not content_graph.publish_date or content_graph.publish_date < datetime.datetime.now():
            evaluation = content.get_user_evaluation(request.user)

    context = {
        'course': course,
        'course_slug': course_slug,
    }
                             
    rendered_content = content.rendered_markup(request, context)

    c = RequestContext(request, {
        'course_slug': course_slug,
        'course_name': course.name,
        'content': content,
        'rendered_content': rendered_content,
        'content_name': content.name,
        'content_type': content_type,
        'question': question,
        'choices': choices,
        'evaluation': evaluation,
        'user': user,
    })
    if "frontpage" in kwargs:
        return c
    else:
        t = loader.get_template("courses/contentpage.html")
        return HttpResponse(t.render(c))

def user_profile_save(request):
    """
    Save the submitted form.
    """
    if not request.user.is_authenticated():
        return HttpResponseNotFound()
    if not request.method == "POST":
        return HttpResponseNotFound()
    form = request.POST
    if not set(["first_name", "last_name", "student_id", "study_program"]).issubset(form.keys()):
        return HttpResponseNotFound()

    profile = UserProfile.objects.get(user=request.user)

    request.user.first_name = form["first_name"][:30]
    request.user.last_name = form["last_name"][:30]
    try:
        profile.student_id = int(form["student_id"])
    except ValueError:
        return HttpResponseNotFound()
    profile.study_program = form["study_program"][:80]

    profile.save()
    request.user.save()
    return HttpResponseRedirect('/')

def user_profile(request):
    """
    Allow the user to change information in their profile.
    """
    if not request.user.is_authenticated():
        return HttpResponseNotFound()

    profile = UserProfile.objects.get(user=request.user)

    t = loader.get_template("courses/userprofile.html")
    c = RequestContext(request, {
        'username': request.user.username,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'student_id': profile.student_id,
        'study_program': profile.study_program,
    })
    return HttpResponse(t.render(c))

def user(request, user_name):
    '''Shows user information to the requesting user. The amount of information depends on who the
    requesting user is.'''
    if request.user == "AnonymousUser":
        # TODO: Don't allow anons to view anything
        # Return 404 even if the users exists to prevent snooping around
        # Distinguishing 403 and 404 here would give away information
        return HttpResponseNotFound()
    elif request.user == user_name:
        # TODO: Allow the user to view their own info and edit some of it
        pass
    elif request.user == "mdf":
        # TODO: Allow admins to view useful information regarding the user they've requested
        pass
    else:
        # TODO: Allow normal users to view some very basic information?
        pass
    
    checkboxexercise_answers = UserCheckboxExerciseAnswer.objects.filter(user=request.user)
    multiplechoiceexercise_answers = UserMultipleChoiceExerciseAnswer.objects.filter(user=request.user)
    textfieldexercise_answers = UserTextfieldExerciseAnswer.objects.filter(user=request.user)
    fileexercise_answers = UserFileUploadExerciseAnswer.objects.filter(user=request.user)

    t = loader.get_template("courses/userinfo.html")
    c = RequestContext(request, {
        'checkboxexercise_answers': checkboxexercise_answers,
        'multiplechoiceexercise_answers': multiplechoiceexercise_answers,
        'textfieldexercise_answers': textfieldexercise_answers,
        'fileexercise_answers': fileexercise_answers,
    })
    return HttpResponse(t.render(c))

def calendar_post(request, calendar_id, event_id):
    if not request.user.is_authenticated():
        return HttpResponseNotFound()
    if not request.method == "POST":
        return HttpResponseNotFound()
    form = request.POST

    event_id = int(event_id)

    try:
        calendar_date = CalendarDate.objects.get(id=event_id)
    except CalendarDate.DoesNotExist:
        return HttpResponseNotFound("Error: the selected calendar does not exist.")

    if "reserve" in form.keys():
        # TODO: How to make this atomic?
        reservations = CalendarReservation.objects.filter(calendar_date_id=event_id)
        if reservations.count() >= calendar_date.reservable_slots:
            return HttpResponse("This event is already full.")
        user_reservations = reservations.filter(user=request.user)
        if user_reservations.count() >= 1:
            return HttpResponse("You have already reserved a slot in this event.")

        new_reservation = CalendarReservation(calendar_date_id=event_id, user=request.user)
        new_reservation.save()
        # TODO: Check that we didn't overfill the event
        return HttpResponse("Slot reserved!")
    elif "cancel" in form.keys():
        user_reservations = CalendarReservation.objects.filter(calendar_date_id=event_id, user=request.user)
        if user_reservations.count() >= 1:
            user_reservations.delete()
            return HttpResponse("Reservation cancelled.")
        else:
            return HttpResponse("Reservation already cancelled.")
    else:
        return HttpResponseNotFound()

def show_answers(request, user, course, exercise):
    """
    Show the user's answers for a specific exercise on a specific course.
    """
    if request.user.is_authenticated() and (request.user.username == user or request.user.is_staff):
        pass
    else:
        return HttpResponseForbidden("You're only allowed to view your own answers.")

    try:
        user_obj = User.objects.get(username=user)
    except User.DoesNotExist as e:
        return HttpResponseNotFound("No such user %s" % user)

    try:
        course_obj = Course.objects.get(slug=course)
    except Course.DoesNotExist as e:
        return HttpResponseNotFound("No such course %s" % course)
    
    try:
        exercise_obj = ContentPage.objects.get(slug=exercise).get_type_object()
    except ContentPage.DoesNotExist as e:
        return HttpResponseNotFound("No such exercise %s" % exercise)

    content_type = exercise_obj.content_type
    question = exercise_obj.question
    choices = exercise_obj.get_choices()

    # TODO: Error checking for exercises that don't belong to this course
    
    answers = []

    if content_type == "MULTIPLE_CHOICE_EXERCISE":
        answers = UserMultipleChoiceExerciseAnswer.objects.filter(user=user_obj, exercise=exercise_obj)
    elif content_type == "CHECKBOX_EXERCISE":
        answers = UserCheckboxExerciseAnswer.objects.filter(user=user_obj, exercise=exercise_obj)
    elif content_type == "TEXTFIELD_EXERCISE":
        answers = UserTextfieldExerciseAnswer.objects.filter(user=user_obj, exercise=exercise_obj)
    elif content_type == "FILE_UPLOAD_EXERCISE":
        answers = UserFileUploadExerciseAnswer.objects.filter(user=user_obj, exercise=exercise_obj)

    # TODO: Own subtemplates for each of the exercise types.
    t = loader.get_template("courses/user_exercise_answers.html")
    c = RequestContext(request, {
        'answers': answers,
    })
    return HttpResponse(t.render(c))

def help_list(request):
    return HttpResponse()

def markup_help(request):
    markups = markupparser.MarkupParser.get_markups()
    t = loader.get_template("courses/markup-help.html")
    c = RequestContext(request, {
        'markups': markups,
    })
    return HttpResponse(t.render(c))
