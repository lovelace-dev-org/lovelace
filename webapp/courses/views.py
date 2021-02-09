"""
Django views for rendering the course contents and checking exercises.
"""
import datetime
import json
from html import escape
from collections import namedtuple

import redis

import magic

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect,\
    HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed,\
    HttpResponseServerError, HttpResponseBadRequest
from django.db import transaction
from django.db.models import Q
from django.template import Template, loader, engines
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import File
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.contrib import messages

from reversion import revisions as reversion
from reversion.models import Version

from lovelace.celery import app as celery_app
import courses.tasks as rpc_tasks
from courses.tasks import get_celery_worker_status

from courses.models import *
from courses.forms import *
from feedback.models import *

from routine_exercise.models import RoutineExerciseAnswer

from allauth.account.forms import LoginForm

import courses.markupparser as markupparser
import courses.blockparser as blockparser
import django.conf
from django.contrib import auth
from django.shortcuts import redirect

from utils.access import is_course_staff, determine_media_access, ensure_enrolled_or_staff, ensure_owner_or_staff, determine_access, ensure_staff
from utils.archive import find_version_with_filename
from utils.content import first_title_from_content
from utils.files import generate_download_response
from utils.management import CourseContentAdmin
from utils.notify import send_error_report, send_welcome_email

try:
    from shibboleth.app_settings import LOGOUT_URL, LOGOUT_REDIRECT_URL, LOGOUT_SESSION_KEY
except:
    # shibboleth not installed 
    # these are not needed
    LOGOUT_URL = ""
    LOGOUT_REDIRECT_URL = ""
    LOGOUT_SESSION_KEY = ""

JSON_INCORRECT = 0
JSON_CORRECT = 1
JSON_INFO = 2
JSON_ERROR = 3
JSON_DEBUG = 4


def cookie_law(view_func):
    """
    To comply with the European Union cookie law, display a warning about the
    site using cookies. When the user accepts cookies, set a session variable to
    disable the message.
    """
    def func_wrapper(request, *args, **kwargs):
        if "cookies_accepted" in request.COOKIES:
            if request.COOKIES["cookies_accepted"] == "1":
                request.session["cookies_accepted"] = True
        if request.session.get("cookies_accepted"):
            pass
        else:
            request.session["cookies_accepted"] = False
        return view_func(request, *args, **kwargs)
    return func_wrapper

@cookie_law
def login(request):
    # template based on allauth login page
    t = loader.get_template("courses/login.html")
    c = {
        'login_form': LoginForm(),
        'signup_url': reverse("account_signup")
    }

    if 'shibboleth' in django.conf.settings.INSTALLED_APPS:
        c['shibboleth_login'] = reverse("shibboleth:login")
    else:
        c['shibboleth_login'] = False

    return HttpResponse(t.render(c, request))

@cookie_law    
def logout(request):
    # template based on allauth logout page
    t = loader.get_template("courses/logout.html")   
    
    if request.method == "POST":
        # handle shibboleth logout
        # from shibboleth login view
        
        auth.logout(request)
        request.session[LOGOUT_SESSION_KEY] = True
        target = LOGOUT_REDIRECT_URL
        logout = LOGOUT_URL % target
        return redirect(logout)        
    
    if request.session.get("shib", None):
        c = {
            "logout_url": reverse("courses:logout") 
        }
    else:
        c = {
            "logout_url": reverse("account_logout")
        }
    return HttpResponse(t.render(c, request))

@cookie_law
def index(request):
    course_list = Course.objects.all()
    
    t = loader.get_template("courses/index.html")
    c = {
        'course_list': course_list,
    }
    return HttpResponse(t.render(c, request))

@cookie_law
def course_instances(request, course):
    return HttpResponse("here be instances for this course")

def check_exercise_accessible(request, course, instance, content):

    embedded_links = EmbeddedLink.objects.filter(
        embedded_page_id=content.id, instance=instance
    )
    content_graph_links = ContentGraph.objects.filter(
        instance=instance, content=content
    )
    
    if content_graph_links.first() is None and embedded_links.first() is None:
        return {'error': HttpResponseNotFound(
            "Content {} is not linked to course {}!".format(
                content.slug, course.slug
            )
        )}

    return {
        'embedded_links': embedded_links,
        'content_graph_links': content_graph_links,
        'error': None,
    }

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
        from utils.management import CourseContentAdmin
        contents = ContentGraph.objects.filter(
            instance=instance,
            ordinal_number__gt=0,
            parentnode=None
        ).order_by('ordinal_number')
        context["course_staff"] = True
        content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
        available_content = content_access.defer("content").all()
        try:
            frontpage_id = instance.frontpage.id
        except AttributeError:
            frontpage_id = 0
    else:
        contents = ContentGraph.objects.filter(
            instance=instance,
            ordinal_number__gt=0,
            visible=True,
            parentnode=None
        ).order_by('ordinal_number')
        context["course_staff"] = False 
    
    if len(contents) > 0:
        tree = []
        tree.append((mark_safe('>'), None, None, None, None, None, 0))
        for content_ in contents:
            course_tree(tree, content_, request.user, instance)
        tree.append((mark_safe('<'), None, None, None, None, None, 0))
        context["content_tree"] = tree

    t = loader.get_template("courses/course.html")
    return HttpResponse(t.render(context, request))

def course_tree(tree, node, user, instance_obj):
    embedded_links = EmbeddedLink.objects.filter(parent=node.content.id, instance=instance_obj)
    embedded_count = len(embedded_links)
    page_count = node.content.count_pages(instance_obj)
    
    correct_embedded = 0
    
    evaluation = ""
    if user.is_authenticated:
        exercise = node.content
        evaluation = exercise.get_user_evaluation(user, instance_obj)

        if embedded_count > 0:
            
            grouped = embedded_links.exclude(embedded_page__evaluation_group="")
            group_repr = grouped.order_by("embedded_page__evaluation_group")\
                .distinct("embedded_page__evaluation_group")
            
            embedded_count -= (grouped.count() - group_repr.count())
            
            for link in group_repr:
                if link.embedded_page.get_user_evaluation(
                    user, instance_obj
                    ) in ("correct", "credited"):
                    
                    correct_embedded += 1
            
            for emb_exercise in embedded_links.filter(embedded_page__evaluation_group="").values_list('embedded_page', flat=True):
                emb_exercise = ContentPage.objects.get(id=emb_exercise)
                #print(emb_exercise.name)
                correct_embedded += 1 if emb_exercise.get_user_evaluation(user, instance_obj) == "correct" else 0
    
    list_item = (node.content, node.id, evaluation, correct_embedded, embedded_count, node.visible, page_count)
    
    if list_item not in tree:
        tree.append(list_item)

    if is_course_staff(user, instance_obj):
        children = ContentGraph.objects.filter(parentnode=node, instance=instance_obj).order_by('ordinal_number')
    else:
        children = ContentGraph.objects.filter(parentnode=node, instance=instance_obj, visible=True).order_by('ordinal_number')
    
    if len(children) > 0:
        tree.append((mark_safe('>'), None, None, None, None, None, 0))
        for child in children:
            course_tree(tree, child, user, instance_obj)
        tree.append((mark_safe('<'), None, None, None, None, None, 0))

def check_answer_sandboxed(request, content_slug):
    """
    Saves and evaluates a user's answer to an exercise and sends the results
    back to the user in sanboxed mode.
    """

    course_slug = "sandbox"
    
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])

    user = request.user
    if not user.is_authenticated or not user.is_active or not user.is_staff:
        return JsonResponse({
            'result': 'Only logged in admins can send their answers for evaluation!'
        })

    content = ContentPage.objects.get(slug=content_slug)
    
    user = request.user
    ip = request.META.get('REMOTE_ADDR')
    answer = request.POST
    files = request.FILES

    exercise = content.get_type_object()
    
    try:
        answer_object = exercise.save_answer(user, ip, answer, files)
    except InvalidExerciseAnswerException as e:
        return JsonResponse({
            'result': str(e)
        })
    evaluation = exercise.check_answer(user, ip, answer, files, answer_object)
    if not exercise.manually_evaluated:
        if exercise.content_type == "FILE_UPLOAD_EXERCISE":
            task_id = evaluation["task_id"]
            return check_progress(request, None, content_slug, task_id)
        exercise.save_evaluation(user, evaluation, answer_object)
        evaluation["manual"] = False
    else:
        evaluation["manual"] = True

    # TODO: Errors, hints, comments in JSON
    t = loader.get_template("courses/exercise-evaluation.html")
    return JsonResponse({
        'result': t.render(evaluation),
        'evaluation': evaluation.get("evaluation"),
    })

@ensure_enrolled_or_staff
def check_answer(request, course, instance, content, revision):
    """
    Saves and evaluates a user's answer to an exercise and sends the results
    back to the user.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])

    # TODO: Ensure that the content revision really belongs to the course instance

    # Check if a deadline exists and if it has already passed
    try:
        content_graph = ContentGraph.objects.get(instance=instance, content=content)
    except ContentGraph.DoesNotExist as e:
        pass
    else:
        if content_graph is not None:
            if not content_graph.deadline or datetime.datetime.now() < content_graph.deadline:
                pass
            else:
                # TODO: Use a template!
                return JsonResponse({
                    'result': _('The deadline for this exercise (%s) has passed. Your answer will not be evaluated!') % (content_graph.deadline)
                })

    user = request.user
    ip = request.META.get('REMOTE_ADDR')
    answer = request.POST
    files = request.FILES

    exercise = content
    
    if revision == "head":
        latest = Version.objects.get_for_object(content).latest("revision__date_created")
        answered_revision = latest.revision_id
        revision = None
    else:
        answered_revision = revision

    try:
        answer_object = exercise.save_answer(content, user, ip, answer, files, instance, answered_revision)
    except InvalidExerciseAnswerException as e:
        return JsonResponse({
            'result': str(e)
        })
    evaluation = exercise.check_answer(content, user, ip, answer, files, answer_object, revision)
    if not exercise.manually_evaluated:
        if exercise.content_type == "FILE_UPLOAD_EXERCISE":
            task_id = evaluation["task_id"]
            return check_progress(request, course, instance, content, revision, task_id)
        exercise.save_evaluation(content, user, evaluation, answer_object)
        evaluation["manual"] = False
    else:
        evaluation["manual"] = True

    msg_context = {
        'course_slug': course.slug,
        'instance_slug': instance.slug,
        'instance': instance,
        'content_page': content
    }
    hints = ["".join(markupparser.MarkupParser.parse(msg, request, msg_context)).strip()
             for msg in evaluation.get('hints', [])]

    answer_count = exercise.get_user_answers(exercise, user, instance).count()
    answer_count_str = get_answer_count_meta(answer_count)

    # TODO: Errors, hints, comments in JSON
    t = loader.get_template("courses/exercise-evaluation.html")
    total_evaluation = exercise.get_user_evaluation(user, instance)
    #print(evaluation)
    
    data = {
        'result': t.render(evaluation),
        'hints': hints,
        'evaluation': evaluation.get("evaluation"),
        'answer_count_str': answer_count_str,
        'next_instance': evaluation.get('next_instance', None),
        'total_instances': evaluation.get('total_instances', None),
        'total_evaluation': total_evaluation,
    }
    return JsonResponse(data)


@ensure_enrolled_or_staff
def get_repeated_template_session(request, course, instance, content, revision):
    check_results = check_exercise_accessible(request, course, instance, content)
    check_error = check_results.get('error')
    if check_error is not None:
        return check_error

    content = content.get_type_object()
    
    lang_code = translation.get_language()

    # If a user has an unfinished session, pick that one
    open_sessions = RepeatedTemplateExerciseSession.objects.filter(
        exercise=content, user=request.user, language_code=lang_code,
        repeatedtemplateexercisesessioninstance__userrepeatedtemplateinstanceanswer__isnull=True
    )
    
    session = open_sessions.exclude(repeatedtemplateexercisesessioninstance__userrepeatedtemplateinstanceanswer__correct=False).distinct().first()

    #print(session)
    if session is None:
        with transaction.atomic():
            session = RepeatedTemplateExerciseSession.objects.filter(exercise=content, user__isnull=True, language_code=lang_code).first()
            if session is not None:
                session.user = request.user
                session.save()
            else:
                # create a new one, no need for atomic anymore
                if revision == "head": revision = None
                # TODO: DO NOTHING AND FORGET THE TASK IF CELERY IS NOT WORKING!
                # TODO: Add an expire date
                celery_status = rpc_tasks.get_celery_worker_status()
                if 'errors' in celery_status.keys():
                    data = {
                        'ready': True,
                        'rendered_template': _("Error, exercise backend unavailable."),
                    }
                else:
                    result = rpc_tasks.generate_repeated_template_session.delay(
                        user_id=request.user.id,
                        instance_id=instance.id,
                        exercise_id=content.id,
                        lang_code=lang_code,
                        revision=revision
                    )
                    # TODO: Check that the task was successfully launched
                    rerequest_url = reverse('courses:get_repeated_template_session',
                                            kwargs={'course': course,
                                                    'instance': instance,
                                                    'content': content,
                                                    'revision': "head" if revision is None else revision,
                                            })
                    data = {
                        'ready': False,
                        'redirect': rerequest_url,
                    }
                return JsonResponse(data)

    # Pick the first unfinished instance
    session_instance = RepeatedTemplateExerciseSessionInstance.objects.filter(session=session, userrepeatedtemplateinstanceanswer__isnull=True).order_by('ordinal_number').first()
    #usession_instance)

    session_template = session_instance.template
    variables = session_instance.variables
    values = session_instance.values
    
    total_instances = session.total_instances()
    next_instance = session_instance.ordinal_number + 2 if session_instance.ordinal_number + 1 < total_instances else None
    
    #print(session_instance.ordinal_number + 1, " / ", total_instances)
    
    rendered_template = session_instance.template.content_string.format(**dict(zip(variables, values)))
    
    #print(session_instance.repeatedtemplateexercisesessioninstanceanswer_set.first().answer)
    
    template_context = {
        'course_slug': course.slug,
        'instance_slug': instance.slug,
    }
    template_parsed = "".join(markupparser.MarkupParser.parse(rendered_template, request, template_context)).strip()

    data = {
        'ready': True,
        'title': session_template.title,
        'rendered_template': template_parsed,
        'redirect': None,
        'next_instance': next_instance,
        'total_instances': total_instances,
        'progress': "{} / {}".format(session_instance.ordinal_number + 1, total_instances)
    }
    
    return JsonResponse(data)

@ensure_enrolled_or_staff
def check_progress(request, course, instance, content, revision, task_id):
    # Based on https://djangosnippets.org/snippets/2898/
    # TODO: Check permissions
    task = celery_app.AsyncResult(id=task_id)
    info = task.info
    if task.ready():
        return file_exercise_evaluation(request, course, instance, content, revision, task_id, task)
    else:
        celery_status = get_celery_worker_status()
        if "errors" in celery_status:
            data = celery_status
        else:
            progress_url = reverse('courses:check_progress',
                                   kwargs={'course': course,
                                           'instance': instance,
                                           'content': content,
                                           'revision': "head" if revision is None else revision,
                                           'task_id': task_id,})
            if not info: info = task.info # Try again in case the first time was too early
            data = {"state": task.state, "metadata": info, "redirect": progress_url}
        return JsonResponse(data)

def get_answer_count_meta(answer_count):
    # TODO: Maybe refactor
    t = engines['django'].from_string("""{% load i18n %}{% blocktrans count counter=answer_count %}<span class="answer-count">{{ counter }}</span> answer{% plural %}<span class="answer-count">{{ counter }}</span> answers{% endblocktrans %}""")
    return t.render({'answer_count': answer_count})
    
    
def file_exercise_evaluation(request, course, instance, content, revision, task_id, task=None):
    if task is None:
        task = AsyncResult(task_id)
    evaluation_id = task.get()
    task.forget() # TODO: IMPORTANT! Also forget all the subtask results somehow? in tasks.py?
    evaluation_obj = Evaluation.objects.get(id=evaluation_id)
    answer_count = content.get_user_answers(content, request.user, instance).count()
    answer_count_str = get_answer_count_meta(answer_count)

    r = redis.StrictRedis(**settings.REDIS_RESULT_CONFIG)
    evaluation_json = r.get(task_id).decode("utf-8")
    evaluation_tree = json.loads(evaluation_json)
    r.delete(task_id)
    task.forget()

    msg_context = {
        'course_slug': course.slug,
        'instance_slug': instance.slug,
        'instance': instance,
        'content_page': content
    }

    data = compile_evaluation_data(request, evaluation_tree, evaluation_obj, msg_context)
    
    errors = evaluation_tree['test_tree'].get('errors', [])
    if errors:
        if evaluation_tree['timedout']:
            data['errors'] = _("The program took too long to execute and was terminated. Check your code for too slow solutions.")
        else:
            data['errors'] = _("Checking program was unable to finish due to an error. Contact course staff.")
            answer_url = reverse("courses:show_answers", kwargs={
                "user": request.user,
                "course": course,
                "instance": instance,
                "exercise": content
            }) + "#" + str(evaluation_obj.useranswer.id)
            send_error_report(instance, content, revision, errors, answer_url)
        
    data["answer_count_str"] = answer_count_str
    
    return JsonResponse(data)

def compile_evaluation_data(request, evaluation_tree, evaluation_obj, context=None):
    log = evaluation_tree["test_tree"].get("log", [])

    messages = [
        (msg['title'], [
            "".join(markupparser.MarkupParser.parse(msg_msg, request, context)).strip()
            for msg_msg in msg['msgs']
        ])
        for msg in evaluation_tree['test_tree'].get('messages', [])
    ]

    # render all individual messages in the log tree
    for test in log:
        test["title"] = "".join(markupparser.MarkupParser.parse(test["title"], request, context)).strip()
        test["runs"].sort(key=lambda run: run["correct"])
        for run in test["runs"]:
            for output in run["output"]:
                output["msg"] = "".join(markupparser.MarkupParser.parse(output["msg"], request, context)).strip()
    
    debug_json = json.dumps(evaluation_tree, indent=4)

    hints = ["".join(markupparser.MarkupParser.parse(msg, request, context)).strip()
             for msg in evaluation_tree['test_tree'].get('hints', [])]
    triggers = evaluation_tree['test_tree'].get('triggers', [])

    t_file = loader.get_template("courses/file-exercise-evaluation.html")
    c_file = {
        'debug_json': debug_json,
        'evaluation_tree': evaluation_tree["test_tree"],
    }
    t_exercise = loader.get_template("courses/exercise-evaluation.html")
    c_exercise = {
        'evaluation': evaluation_obj.correct,
    }
    t_messages = loader.get_template('courses/exercise-evaluation-messages.html')
    data = {
        'file_tabs': t_file.render(c_file, request),
        'result': t_exercise.render(c_exercise),
        'evaluation': evaluation_obj.correct,
        'points': evaluation_obj.points,
        'messages': t_messages.render({'log': log}),
        'hints': hints,
        'triggers': triggers,
    }
    
    return data
    
@ensure_owner_or_staff
def get_file_exercise_evaluation(request, user, course, instance, exercise, answer):
    from .tasks import generate_results

    results_json = answer.evaluation.test_results
    results_dict = json.loads(results_json)

    evaluation_tree = generate_results(results_dict, 0)
    evaluation_obj = answer.evaluation

    msg_context = {
        'course_slug': course.slug,
        'instance_slug': instance.slug,
        'instance': instance,
        'content_page': exercise
    }

    data = compile_evaluation_data(request, evaluation_tree, evaluation_obj, msg_context)

    if not request.user.is_staff:
        data["triggers"] = []

    t_view = loader.get_template("courses/view-answer-results.html")

    return HttpResponse(t_view.render(data, request))


@cookie_law
def sandboxed_content(request, content_slug, **kwargs):
    try:
        content = ContentPage.objects.get(slug=content_slug)
    except ContentPage.DoesNotExist:
        return HttpResponseNotFound("Content {} does not exist!".format(content_slug))

    user = request.user
    if not user.is_authenticated or not user.is_active or not user.is_staff:
        return HttpResponseForbidden("Only logged in admins can view pages in sandbox!")

    content_type = content.content_type
    question = blockparser.parseblock(escape(content.question, quote=False))
    choices = answers = content.get_choices(content)

    rendered_content = content.rendered_markup(request)

    c = {
        'content': content,
        'content_name': content.name,
        'content_type': content_type,
        'rendered_content': rendered_content,
        'embedded': False,
        'question': question,
        'choices': choices,
        'user': user,
        'sandboxed': True,
    }
    if "frontpage" in kwargs:
        return c
    else:
        t = loader.get_template("courses/contentpage.html")
        return HttpResponse(t.render(c, request))

@cookie_law
def content(request, course, instance, content, pagenum=None, **kwargs):
    content_graph = None
    revision = None
    #if "frontpage" not in kwargs:
    try:
        content_graph = ContentGraph.objects.get(instance=instance, content=content)
    except ContentGraph.DoesNotExist:
        return HttpResponseNotFound("Content {} is not linked to course {}!".format(content.slug, course.slug))
    else:
        if content_graph is None:
            return HttpResponseNotFound("Content {} is not linked to course {}!".format(content.slug, course.slug))
        
    evaluation = None
    answer_count = None
    enrolled = False
    course_staff = False
    if request.user.is_authenticated:
        if request.user.is_active and content.is_answerable() and content.get_user_answers(content, request.user, instance):
            answer_count = content.get_user_answers(content, request.user, instance).count()
        if content_graph and (content_graph.publish_date is None or content_graph.publish_date < datetime.datetime.now()):
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
            
    revision = content_graph.revision
    
    content_type = content.content_type

    context = {
        'course': course,
        'course_slug': course.slug,
        'instance': instance,
        'instance_slug': instance.slug,
        'content_page': content,
        'enrolled': enrolled,
        'course_staff': course_staff
    }

    termbank_contents = cache.get('termbank_contents_{instance}_{lang}'.format(instance=context['instance_slug'], lang=translation.get_language()))
    term_div_data = cache.get('term_div_data_{instance}_{lang}'.format(instance=context['instance_slug'], lang=translation.get_language()))
    if termbank_contents is None or term_div_data is None:
        term_context = context.copy()
        term_context['tooltip'] = True
        term_links = TermToInstanceLink.objects.filter(instance__slug=context["instance_slug"])
        term_div_data = []
        termbank_contents = {}
        #terms = Term.objects.filter(course=course).exclude(Q(description__isnull=True) | Q(description__exact='')).order_by('name')
        terms = []
        for link in term_links:
            if link.revision is None:
                term = link.term
            else:
                term = Version.objects.get_for_object(link.term).get(revision=link.revision)._object_version.object
                
            if term.description:
                terms.append(term)
        
        def sort_by_name(item):
            return item.name
            
        terms.sort(key=sort_by_name)
        
        for term in terms:
            slug = slugify(term.name, allow_unicode=True)
            description = "".join(markupparser.MarkupParser.parse(term.description, request, term_context)).strip()
            tabs = [(tab.title, "".join(markupparser.MarkupParser.parse(tab.description, request, term_context)).strip())
                    for tab in term.termtab_set.all().order_by('id')]
            tags = term.tags
            
            final_links = []
            for link in term.termlink_set.all():
                try:
                    server_side, client_side = link.url.split('#', 1)
                except ValueError:
                    server_side = link.url
                    client_side = None
                
                try:
                    target_content = ContentPage.objects.get(slug=server_side)
                except ContentPage.DoesNotExist:
                    final_address = link.url
                else:
                    final_address = reverse('courses:content', args=[context['course'], context['instance'], target_content])
                    if client_side is not None:
                        final_address = final_address.rstrip('/') + '#' + client_side
                    
                final_links.append({"url": final_address, "text": link.link_text})
                
            term_div_data.append({
                'slug' : slug,
                'description' : description,
                'tabs' : tabs,
                'links' : final_links,
            })

            term_data = {
                'slug' : slug,
                'name' : term.name,
                'tags' : tags.values_list("name", flat=True),
                'alias' : False,
            }

            def get_term_initial(term):
                try:
                    first_char = term.upper()[0]
                except IndexError:
                    first_char = "#"
                else:
                    if not first_char.isalpha():
                        first_char = "#"
                return first_char

            first_char = get_term_initial(term.name)
            
            if first_char in termbank_contents:
                termbank_contents[first_char].append(term_data)
            else:
                termbank_contents[first_char] = [term_data]

                
            aliases = TermAlias.objects.filter(term=term)
            for alias in aliases:
                alias_data = {
                    'slug' : slug,
                    'name' : term.name,
                    'alias' : alias.name,
                }

                first_char = get_term_initial(alias.name)

                if first_char in termbank_contents:
                    termbank_contents[first_char].append(alias_data)
                else:
                    termbank_contents[first_char] = [alias_data]
                    
        cache.set(
            'termbank_contents_{instance}_{lang}'.format(
                instance=context['instance_slug'],
                lang=translation.get_language()
            ),
            termbank_contents,
            timeout=None
        )
        
        cache.set(
            'term_div_data_{instance}_{lang}'.format(
                instance=context['instance_slug'],
                lang=translation.get_language()
            ),
            term_div_data,
            timeout=None
        )
            
    # TODO: Admin link should point to the correct version!

    # TODO: Warn admins if the displayed version is not the current version!

    question = blockparser.parseblock(escape(content.question, quote=False), {"course": course})
    choices = answers = content.get_choices(content, revision=revision)
    rendered_content = content.rendered_markup(request, context, revision, page=pagenum)
    embedded_links = EmbeddedLink.objects.filter(parent=content, instance=instance
                                                 ).select_related("embedded_page")
    embed_dict = {}
    for link in embedded_links:
        embed_dict[link.embedded_page.slug] = link.embedded_page
            

    c = {
        'course': course,
        'course_slug': course.slug,
        'course_name': course.name,
        "instance": instance,
        'instance_name': instance.name,
        'instance_slug': instance.slug,
        'content': content,
        'content_blocks': rendered_content,
        'embedded_pages': embed_dict,
        'rendered_content': rendered_content,
        'embedded': False,
        'content_name': content.name,
        'content_type': content_type,
        'question': question,
        'choices': choices,
        'evaluation': evaluation,
        'answer_count': answer_count,
        'sandboxed': False,
        'termbank_contents': sorted(list(termbank_contents.items())),
        'term_div_data': term_div_data,
        'revision': revision,
        'enrolled': enrolled,
        'course_staff': course_staff
    }
    if "frontpage" in kwargs:
        return c
    else:
        t = loader.get_template("courses/contentpage.html")
        return HttpResponse(t.render(c, request))

def user_profile_save(request):
    """
    Save the submitted form.
    """
    if not request.user.is_authenticated:
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
    request.user.save   ()
    return HttpResponseRedirect('/')

def user_profile(request):
    """
    Allow the user to change information in their profile.
    """
    if not request.user.is_authenticated:
        return HttpResponseNotFound()

    profile = UserProfile.objects.get(user=request.user)

    t = loader.get_template("courses/userprofile.html")
    c = {
        'username': request.user.username,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'student_id': profile.student_id,
        'study_program': profile.study_program,
    }
    return HttpResponse(t.render(c, request))

def user(request, user_name):
    """
    Shows user information to the requesting user. The amount of information
    depends on who the requesting user is.
    """
    user = request.user

    if not (user.is_authenticated and user.is_active): # Don't allow anons to view anything
        return HttpResponseForbidden(_("Please log in to view your information."))
    elif user.is_staff: # Allow admins to view useful information regarding the user they've requested
        pass
    elif user.username != user_name: # Allow the user to view their own info
        return HttpResponseForbidden(_("You are only allowed to view your own information."))

    try:
        target_user = User.objects.get(username=user_name)
    except User.DoesNotExist as e:
        return HttpReponseNotFound("No such user {}".format(user_name))
    
    checkboxexercise_answers = UserCheckboxExerciseAnswer.objects.filter(user=target_user)
    multiplechoiceexercise_answers = UserMultipleChoiceExerciseAnswer.objects.filter(user=target_user)
    textfieldexercise_answers = UserTextfieldExerciseAnswer.objects.filter(user=target_user)
    fileexercise_answers = UserFileUploadExerciseAnswer.objects.filter(user=target_user)
    repeatedtemplateexercise_answers = UserRepeatedTemplateExerciseAnswer.objects.filter(user=target_user)

    t = loader.get_template("courses/userinfo.html")
    c = {
        'checkboxexercise_answers': checkboxexercise_answers,
        'multiplechoiceexercise_answers': multiplechoiceexercise_answers,
        'textfieldexercise_answers': textfieldexercise_answers,
        'fileexercise_answers': fileexercise_answers,
        'repeatedtemplateexercise_answers': repeatedtemplateexercise_answers,
    }
    return HttpResponse(t.render(c, request))

# TODO: calendars should be tied to instances
def calendar_post(request, calendar_id, event_id):
    if not request.user.is_authenticated:
        return HttpResponseNotFound()
    if not request.method == "POST":
        return HttpResponseNotFound()
    form = request.POST

    event_id = int(event_id)

    try:
        calendar_date = CalendarDate.objects.get(id=event_id)
    except CalendarDate.DoesNotExist:
        return HttpResponseNotFound("Error: the selected calendar does not exist.")

    if "reserve" in form.keys() and int(form["reserve"]) == 1:
        # TODO: How to make this atomic? Use with transaction.atomic
        reservations = CalendarReservation.objects.filter(calendar_date_id=event_id)
        if reservations.count() >= calendar_date.reservable_slots:
            return HttpResponse(_("This event is already full."))
        user_reservations = reservations.filter(user=request.user)
        if user_reservations.count() >= 1:
            return HttpResponse(_("You have already reserved a slot in this event."))

        new_reservation = CalendarReservation(calendar_date_id=event_id, user=request.user)
        new_reservation.save()
        # TODO: Check that we didn't overfill the event
        return HttpResponse(_("Slot reserved!"))
    elif "reserve" in form.keys() and int(form["reserve"]) == 0:
        user_reservations = CalendarReservation.objects.filter(calendar_date_id=event_id, user=request.user)
        if user_reservations.count() >= 1:
            user_reservations.delete()
            return HttpResponse(_("Reservation cancelled."))
        else:
            return HttpResponse(_("Reservation already cancelled."))
    else:
        return HttpResponseForbidden()

@ensure_owner_or_staff
def show_answers(request, user, course, instance, exercise):
    """
    Show the user's answers for a specific exercise on a specific course.
    """

    content_type = exercise.content_type
    question = exercise.question
    choices = exercise.get_choices(exercise)
    template = "courses/user-exercise-answers.html"
    
    # TODO: Error checking for exercises that don't belong to this course
    
    answers = []
    
    if content_type == "MULTIPLE_CHOICE_EXERCISE":
        answers = UserMultipleChoiceExerciseAnswer.objects.filter(
            user=user,
            exercise=exercise,
            instance=instance
        )
    elif content_type == "CHECKBOX_EXERCISE":
        answers = UserCheckboxExerciseAnswer.objects.filter(
            user=user,
            exercise=exercise,
            instance=instance
        )
    elif content_type == "TEXTFIELD_EXERCISE":
        answers = UserTextfieldExerciseAnswer.objects.filter(
            user=user,
            exercise=exercise,
            instance=instance
        )
    elif content_type == "FILE_UPLOAD_EXERCISE":
        answers = UserFileUploadExerciseAnswer.objects.filter(
            user=user,
            exercise=exercise,
            instance=instance
        )
    elif content_type == "CODE_REPLACE_EXERCISE":
        answers = UserCodeReplaceExerciseAnswer.objects.filter(
            user=user,
            exercise=exercise,
            instance=instance
        )
    elif content_type == "REPEATED_TEMPLATE_EXERCISE":
        answers = UserRepeatedTemplateExerciseAnswer.objects.filter(
            user=user,
            exercise=exercise,
            instance=instance
        )
    elif content_type == "ROUTINE_EXERCISE":
        answers = exercise.get_user_answers(exercise, user, instance)
        template = "routine_exercise/user-answers.html"

    answers = answers.order_by('-answer_date')

    try:
        link = EmbeddedLink.objects.get(embedded_page=exercise, instance=instance)
    except EmbeddedLink.MultipleObjectsReturned:
        parent = None
        single_linked = False
    else:
        parent = link.parent
        single_linked = True

    title, anchor = first_title_from_content(exercise.content)

    # TODO: Own subtemplates for each of the exercise types.
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
        "student": user,
        "username": user.username,
        "course_staff": user.is_staff
    }
    return HttpResponse(t.render(c, request))

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
            fs_path = os.path.join(getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT), f.fileinfo.name)
            break
    else:
        return HttpResponseForbidden(_("You cannot access this answer."))
    
    return generate_download_response(fs_path)

def download_embedded_file(request, course, instance, mediafile):
    """
    This view function is for downloading media files via the actual site.
    """
    
    #NOTE: hotfix for multiple copies of medialinks
    try:
        file_link = CourseMediaLink.objects.filter(media=mediafile, instance=instance).first()
    except CourseMediaLink.DoesNotExist as e:
        return HttpResponseNotFound("No such file {}".format(mediafile.name))
    
    if file_link.revision is None:
        file_object = file_link.media.file
    else:
        file_object = Version.objects.get_for_object(file_link.media.file).get(revision=file_link.revision)._object_version.object
    
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
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to download media files through this interface."))
    
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


# TODO: limit to owner and course staff
def download_template_exercise_backend(request, exercise_id, field_name, filename):
    
    try:
        exercise_object = RepeatedTemplateExercise.objects.get(id=exercise_id)
    except CourseInstance.DoesNotExist as e:
        return HttpResponseNotFound(_("This exercise does't exist"))
            
    if not determine_access(request.user, exercise_object):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to download files through this interface."))
            
    fileobjects = RepeatedTemplateExerciseBackendFile.objects.filter(exercise=exercise_object)
    try:
        for fileobject in fileobjects:
            if filename == os.path.basename(getattr(fileobject, field_name).name):
                fs_path = os.path.join(settings.PRIVATE_STORAGE_FS_PATH, getattr(fileobject, field_name).name)
                break
            else:
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
    
def help_list(request):
    return HttpResponse()

def markup_help(request):
    markups = markupparser.MarkupParser.get_markups()
    Markup = namedtuple(
        'Markup',
        ['name', 'description', 'example', 'result', 'slug']
    )

    markup_list = (
        Markup(m.name, m.description, m.example, mark_safe("".join(markupparser.MarkupParser.parse(m.example))),
               slugify(m.name, allow_unicode=True))
        for _, m in markups.items()
    )
    
    t = loader.get_template("courses/markup-help.html")
    c = {
        'markups': list(sorted(markup_list)),
    }
    return HttpResponse(t.render(c, request))

def terms(request):
    t = loader.get_template("courses/terms.html")
    c = {}
    return HttpResponse(t.render(c, request))
