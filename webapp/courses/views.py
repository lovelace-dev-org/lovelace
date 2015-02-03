"""
Django views for rendering the course contents and checking exercises.
"""
import re
import random
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
import courses.filecheck_client as filecheck_client

# TODO: Deprecated
class NavURL:
    def __init__(self, url, name):
        self.url = url
        self.name = name

def index(request):
    course_list = Course.objects.all()
    navurls = [NavURL(reverse('courses:index'), _("Courses"))]
    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course_list': course_list,
        'navurls': navurls,
    })
    return HttpResponse(t.render(c))
 
def course(request, course_slug, **kwargs):
    selected_course = Course.objects.get(slug=course_slug)
    navurls = [NavURL(reverse('courses:index'), _("Courses")),
               NavURL(reverse('courses:course', kwargs={"course_slug":course_slug}), selected_course.name),]

    frontpage = selected_course.frontpage

    if frontpage:
        content_slug = frontpage.slug
        kwargs["frontpage"] = True
        contextdict = content(request, course_slug, content_slug, **kwargs)
    else:
        contextdict = {}

    contextdict["course"] = selected_course 
    contextdict["navurls"] = navurls 
    contextdict["title"] = '%s' % selected_course.name

    contents = selected_course.contents.all().order_by('parentnode', '-id')
    if len(contents) > 0:
        tree = []    
        tree.append((mark_safe('>'), None))
        for content_ in contents:
            dirtree(tree, content_, request.user)
        tree.append((mark_safe('<'), None))
        contextdict["content_tree"] = tree

    t = loader.get_template("courses/course.html")
    c = RequestContext(request, contextdict)
    return HttpResponse(t.render(c))

def dirtree(tree, node, user):
    result = "not_answered"
    if user.is_authenticated():
        evaluations = None
        if node.content.content_type == "CHECKBOX_EXERCISE":
            evaluations = Evaluation.objects.filter(useranswer__usercheckboxexerciseanswer__exercise=node.content, useranswer__user=user)
        elif node.content.content_type == "MULTIPLE_CHOICE_EXERCISE":
            evaluations = Evaluation.objects.filter(useranswer__usermultiplechoiceexerciseanswer__exercise=node.content, useranswer__user=user)
        elif node.content.content_type == "TEXTFIELD_EXERCISE":
            evaluations = Evaluation.objects.filter(useranswer__usertextfieldexerciseanswer__exercise=node.content, useranswer__user=user)
        elif node.content.content_type == "FILE_UPLOAD_EXERCISE":
            evaluations = Evaluation.objects.filter(useranswer__userfileuploadexerciseanswer__exercise=node.content, useranswer__user=user)
        
        if not evaluations:
            result = "not_answered"
        else:
            correct = evaluations.filter(points__gt=0.0)
            if correct:
                result = "correct"
            else:
                result = "incorrect"

    list_item = (node.content, result)
    if list_item not in tree:
        tree.append(list_item)

    children = ContentGraph.objects.filter(parentnode=node)
    if len(children) > 0:
        tree.append((mark_safe('>'), None))
        for child in children:
            dirtree(tree, child, user)
        tree.append((mark_safe('<'), None))

def check_answer(request, course_slug, content_slug, **kwargs):
    """Validates an answer to an exercise."""
    if request.method == "POST":
        # <DEBUG>
        print(request.POST)
        # </DEBUG>
        pass
    else:
        return HttpResponseNotAllowed(['POST'])

    selected_course = Course.objects.get(slug=course_slug)
    content = ContentPage.objects.get(slug=content_slug)
    # TODO: Ensure that the content really belongs to the course

    # Check if a deadline exists and if it has already passed
    try:
        content_graph = selected_course.contents.get(content=content)
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
    exercise.save_evaluation(user, evaluation)

    # TODO: In case of errors, send a 500
    if "errors" in evaluation.keys() and evaluation["errors"]:
        return HttpResponseServerError()

    if exercise.content_type == "FILE_UPLOAD_EXERCISE":
        task_id = evaluation["task_id"]
        return HttpResponseRedirect(reverse('courses:check_progress',
                                            kwargs={"course_slug": course_slug,
                                                    "content_slug": content_slug,
                                                    "task_id": task_id}))

    t = loader.get_template("courses/exercise_evaluation.html")
    c = Context({
        'evaluation': evaluation,
    })
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

def get_user_exercise_info(user, exercise, exercisetype, pub_date=None):
    if not pub_date:
        pub_date = datetime.datetime(2000, 1, 1)
    evaluations = None
    if exercisetype == "checkbox":
        if not evaluations:
            evaluations = Evaluation.objects.filter(useranswer__usercheckboxexerciseanswer__exercise=exercise, useranswer__user=user, useranswer__answer_date__gte=pub_date)
    elif exercisetype == "multiplechoice":
        if not evaluations:
            evaluations = Evaluation.objects.filter(useranswer__usermultiplechoiceexerciseanswer__exercise=exercise, useranswer__user=user, useranswer__answer_date__gte=pub_date)
    elif exercisetype == "textfield":
        if not evaluations:
            evaluations = Evaluation.objects.filter(useranswer__usertextfieldexerciseanswer__exercise=exercise, useranswer__user=user, useranswer__answer_date__gte=pub_date)
    elif exercisetype == "file":
        if not evaluations:
            evaluations = Evaluation.objects.filter(useranswer__userfileuploadexerciseanswer__exercise=exercise, useranswer__user=user, useranswer__answer_date__gte=pub_date)

    if not evaluations:
        result = "not_answered"
    else:
        correct = evaluations.filter(correct=True)
        if correct:
            result = "correct"
        else:
            result = "incorrect"

    return result

def content(request, course_slug, content_slug, **kwargs):
    print("Ollaan contentissa.")

    selected_course = Course.objects.get(slug=course_slug)
    # TODO: Ensure content is part of course!
    content = ContentPage.objects.get(slug=content_slug)
    pages = [content]

    content_graph = None
    try:
        content_graph = selected_course.contents.get(content=content)
    except ContentGraph.DoesNotExist as e:
        pass

    exercise = content.get_type_object()
    content_type = exercise.content_type
    question = exercise.question
    choices = answers = exercise.get_choices()

    exercise_evaluation = None
    if request.user.is_authenticated():
        if not content_graph or not content_graph.publish_date or content_graph.publish_date < datetime.datetime.now():
            exercise_evaluation = get_user_exercise_info(request.user, content, content_type)

    admin_url = content.get_admin_change_url()

    try:
        question = blockparser.parseblock(escape(question))
    except TypeError: # It was NoneType # TODO: what was?
        pass
    except AttributeError: # It was NoneType
        pass

    emb_content_type = None
    contains_embedded_exercise = False

    navurls = [NavURL(reverse('courses:index'), _("Courses")),
               NavURL(reverse('courses:course', kwargs={"course_slug":course_slug}), selected_course.name),
               NavURL(reverse('courses:content', kwargs={"course_slug":course_slug, "content_slug":content.slug}), content.name)]

    context = {
        'course': selected_course,
        'course_slug': course_slug,
    }
                             
    rendered_content = content.rendered_markup(request, context)
    rc = rendered_content
    #rct = Template(rendered_content)
    #rcc = Context({})
    #rc = rct.render(rcc)

    """
    rendered_content = u''
    unparsed_content = re.split(r"\r\n|\r|\n", content.content)

    parser = content_parser.ContentParser(iter(unparsed_content))
    parser.set_fileroot(kwargs["raippa_root"])
    parser.set_mediaurl(kwargs["media_url"])
    parser.set_coursename(training_name)
    for line in parser.parse():
        # Embed a file, page or a video (TODO: Use custom template tags for a nicer solution)
        include_file_re = re.search("{{\s+(?P<filename>.+)\s+}}", line)
        if include_file_re:
            # It's an embedded source code file
            if include_file_re.group("filename") == parser.get_current_filename():
                # Read the embedded file into file_contents, then
                # syntax highlight it, then replace the placeholder
                # with the contents
                try:
                    file_contents = codecs.open(File.objects.get(name=include_file_re.group("filename")).fileinfo.path, "r", "utf-8").read()
                except File.DoesNotExist as e:
                    line = u'<div class="parser_warning">Warning: file %s not found!</div>' % (include_file_re.group("filename"))
                else:
                    file_contents = highlight(file_contents, PythonLexer(), HtmlFormatter(nowrap=True))
                    line = line.replace(include_file_re.group(0), file_contents)
            # It's an embedded video
            elif include_file_re.group("filename") == parser.get_current_videoname():
                try:
                    video = Video.objects.get(name=parser.get_current_videoname()).link
                except Video.DoesNotExist as e:
                    line = u'<div class="parser_warning">Warning: video %s not found!</div>' % (include_file_re.group("filename"))
                else:
                    line = line.replace(include_file_re.group(0), video)
            # It's an embedded image
            elif include_file_re.group("filename") == parser.get_current_imagename():
                try:
                    image = Image.objects.get(name=parser.get_current_imagename()).fileinfo.url
                except Image.DoesNotExist as e:
                    line = u'<div class="parser_warning">Warning: image %s not found!</div>' % (include_file_re.group("filename"))
                else:
                    line = line.replace(include_file_re.group(0), image)
            # It's an embedded calendar
            elif include_file_re.group("filename") == parser.get_current_calendarname():
                try:
                    calendar = Calendar.objects.get(name=parser.get_current_calendarname())
                    cal_dates = CalendarDate.objects.filter(calendar=calendar)
                    cal_reservations = {}
                    user_has_slot = False
                    reserved_event_name = None
                    event_users = {}
                    for date in cal_dates:
                        cal_reservations[date] = CalendarReservation.objects.filter(calendar_date=date)
                        if request.user.is_authenticated():
                            reservation_by_user = cal_reservations[date].filter(user=request.user)
                            if reservation_by_user.count() >= 1:
                                user_has_slot = True
                                reserved_event_name = date.event_name
                            if request.user.is_staff:
                                event_user_list = list(User.objects.filter(id__in=list(cal_reservations[date].values_list('user', flat=True))))
                                event_users[date] = event_user_list
                        else:
                            pass
                except Calendar.DoesNotExist as e:
                    line = u'<div class="parser_warning">Warning: calendar %s not found!</div>' % (include_file_re.group("filename"))
                else:
                    cal_t = loader.get_template("courses/calendar.html")
                    cal_c = RequestContext(request, {
                        'cal_id': calendar.id,
                        'cal_reservations': cal_reservations,
                        'event_users': event_users,
                        'user_has_slot': user_has_slot,
                        'reserved_event_name': reserved_event_name,
                    })
                    cal_rendered = cal_t.render(cal_c)
                    line = line.replace(include_file_re.group(0), cal_rendered)
            # It's an embedded task
            elif include_file_re.group("filename") == parser.get_current_taskname():
                print(parser.get_current_taskname())
                try:
                    embedded_content = ContentPage.objects.get(url_name=parser.get_current_taskname())
                except ContentPage.DoesNotExist as e:
                    line = u'<div class="parser_warning">Warning: embedded task %s not found!</div>' % (include_file_re.group("filename"))
                    rendered_content += line
                    continue
                pages.append(embedded_content)
                unparsed_embedded_content = re.split(r"\r\n|\r|\n", embedded_content.content)
                embedded_parser = content_parser.ContentParser(iter(unparsed_embedded_content))
                rendered_em_content = u''
                for emline in embedded_parser.parse():
                    rendered_em_content += emline
                
                emb_tasktype, emb_question, emb_choices, emb_answers = get_task_info(embedded_content)
                emb_admin_url = ""
                if emb_tasktype:
                    contains_embedded_task = True
                    tasktypes = {"radiobutton":"radiobuttontask",
                                 "checkbox":"checkboxtask",
                                 "textfield":"textfieldtask",
                                 "file":"fileuploadexercise",
                                 "lecture":"lecturepage",}
                    emb_admin_url = reverse("admin:courses_%s_change" % tasktypes[emb_tasktype], args=(embedded_content.id,))

                if request.user.is_authenticated():
                    if not content_graph or not content_graph.publish_date:
                        #emb_task_evaluation = get_user_task_info(request.user, embedded_content, emb_tasktype)
                        emb_task_evaluation = None
                        pass
                    else:
                        emb_task_evaluation = get_user_task_info(request.user, embedded_content, emb_tasktype, content_graph.publish_date)
                else:
                    emb_task_evaluation = None

                try:
                    emb_question = blockparser.parseblock(escape(emb_question))
                except TypeError: # It was NoneType
                    pass
                except AttributeError: # It was NoneType
                    pass

                emb_t = loader.get_template("courses/task.html")
                emb_c = RequestContext(request, {
                    'embedded_task': True,
                    'emb_content': rendered_em_content,
                    'emb_admin_url': emb_admin_url,
                    'training': selected_course,
                    'content_name': embedded_content.name,
                    'content_name_id': embedded_content.url_name,
                    'content_urlname': embedded_content.url_name,
                    'answer_check_url': reverse('courses:training', kwargs={"training_name":training_name}),
                    'tasktype': emb_tasktype,
                    'question': emb_question,
                    'choices': emb_choices,
                    'evaluation': emb_task_evaluation,
                })
                rendered_em_content = emb_t.render(emb_c)
                line = line.replace(include_file_re.group(0), rendered_em_content)
                
        rendered_content += line
    """

    c = RequestContext(request, {
        'embedded_exercise': False,
        'contains_embedded_exercise': contains_embedded_exercise,
        'course_slug': course_slug,
        'content': content,
        'rendered_content': rc, #rendered_content,
        'content_name': content.name,
        'content_name_id': content.slug,
        'content_urlname': content.slug,
        'admin_url': admin_url,
        'navurls': navurls,
        'title': '%s - %s' % (content.name, selected_course.name),
        'answer_check_url': reverse('courses:course', kwargs={"course_slug":course_slug}),
        'emb_content_type': emb_content_type,
        'content_type': content_type,
        'question': question,
        'choices': choices,
        'evaluation': exercise_evaluation,
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

def image_download(request, imagename, **kwargs):
    try:
        file_path = Image.objects.get(name=imagename).fileinfo.path
    except Image.DoesNotExist:
        try:
            file_path = Image.objects.get(fileinfo='images/'+imagename).fileinfo.path
        except Image.DoesNotExist:
            file_path = ""

    mimetypes.init()
    try:
        fd = open(file_path, "rb")
        mime_type_guess = mimetypes.guess_type(file_path)
        response = HttpResponse(fd, mime_type_guess[0])
        return response
    except IOError:
        return HttpResponseNotFound()

def file_download(request, filename, **kwargs):
    try:
        file_path = File.objects.get(name=filename).fileinfo.path
    except File.DoesNotExist:
        try:
            file_path = File.objects.get(fileinfo='files/'+filename).fileinfo.path
        except File.DoesNotExist:
            try:
                file_path = FileExerciseTestIncludeFile.objects.get(fileinfo=filename).fileinfo.path
            except File.DoesNotExist:
                file_path = ""

    #file_path = os.path.join(kwargs['media_root'], 'files', filename)
    mimetypes.init()
    # TODO: Check user rights!
    try:
        #file_path = os.path.join(kwargs["media_root"], course_name, filename)
        fd = open(file_path, "rb")
        mime_type_guess = mimetypes.guess_type(file_path)
        response = HttpResponse(fd, mime_type_guess[0])
        #response['Content-Disposition'] = 'attachment; filename=%s' % (filename) # Force download?
        return response
    except IOError:
        return HttpResponseNotFound()

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
