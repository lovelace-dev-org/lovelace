import reversion
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from django.template import loader
from django.utils import translation
from django.utils.translation import ugettext as _
from courses import markupparser
from faq.models import FaqQuestion, FaqToInstanceLink
from faq.forms import FaqQuestionForm, FaqLinkForm
from faq.utils import cache_panel, regenerate_cache, render_panel
from utils.access import ensure_staff, is_course_staff
from utils.archive import get_single_archived

def get_faq_panel(request, course, instance, exercise):
    preopen_hooks = request.GET.getlist("preopen")
    return HttpResponse(render_panel(request, course, instance, exercise, preopen_hooks))
    
@ensure_staff
def save_question(request, course, instance, exercise):
    if request.method == "POST":
        if instance.frozen:
            return HttpResponseForbidden(_("Cannot edit FAQ for frozen instance"))
    
        try:
            question = FaqQuestion.objects.filter(hook=request.POST["hook"]).first()
        except KeyError:
            return HttpResponseBadRequest()
        
        if request.POST["action"] == "create":
            form = FaqQuestionForm(request.POST)
        else:
            form = FaqQuestionForm(request.POST, instance=question)
        if form.is_valid():
            with reversion.create_revision():
                saved_question = form.save(commit=True)
                reversion.set_user(request.user)
            if question is None:
                link = FaqToInstanceLink(
                    question=saved_question,
                    instance=instance,
                    exercise=exercise,
                )
                link.save()
            regenerate_cache(instance, exercise)            
            content = render_panel(request, course, instance, exercise)
            return JsonResponse({"content": content})
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        return HttpResponseBadRequest()
        
@ensure_staff
def get_editable_question(request, course, instance, exercise, hook):
    try:
        question = FaqQuestion.objects.get(hook=hook)
    except FaqQuestion.DoesNotExist:
        return HttpResponseNotFound()
    
    return JsonResponse({
        "question": question.question,
        "answer": question.answer,
        "hook": question.hook
    })
    
@ensure_staff
def link_question(request, course, instance, exercise):
    try:
        question = FaqQuestion.objects.get(
            hook=request.POST["question_select"],
            faqtoinstancelink__instance=instance
        )
    except FaqQuestion.DoesNotExist:
        return HttpResponseNotFound()
        
    link = FaqToInstanceLink(
        exercise=exercise,
        instance=instance,
        question=question,
    )
    link.save()
    regenerate_cache(instance, exercise)            
    content = render_panel(request, course, instance, exercise)
    return JsonResponse({"content": content})
    
@ensure_staff
def unlink_question(request, course, instance, exercise, hook):
    if request.method == "POST":
        try:
            FaqToInstanceLink.objects.get(
                instance=instance,
                exercise=exercise,
                question__hook=hook
            ).delete()
        except FaqToInstanceLink.DoesNotExist:
            return HttpResponseNotFound(_("The question is not linked"))
        
        regenerate_cache(instance, exercise)
        return HttpResponse(status=204)
    else:
        return HttpResponseNotAllowed(["POST"])
        
    
    
    
    