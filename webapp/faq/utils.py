from django.conf import settings
from django.core.cache import cache
from django.template import loader
from django.utils import translation
from courses import markupparser
from faq.models import FaqQuestion, FaqToInstanceLink
from faq.forms import FaqQuestionForm, FaqLinkForm
from utils.access import is_course_staff
from utils.archive import get_single_archived


def cache_panel(instance, exercise, lang_code):
    faq_links = FaqToInstanceLink.objects.filter(
        instance=instance,
        exercise=exercise,
    ).order_by("question__question")

    exercise_faq = []
    
    with translation.override(lang_code):
        for link in faq_links:
            if link.revision is None:
                faq = link.question
            else:
                faq = get_single_archived(link.question, link.revision)
            
            markup_gen = markupparser.MarkupParser.parse(faq.answer)
            answer_body = ""
            for chunk in markup_gen:
                if isinstance(chunk, str):
                    answer_body += chunk
                else:
                    raise ValueError("Embedded content is not allowed in panel content")
                
            exercise_faq.append((faq.hook, faq.question, answer_body))
        
    cache.set(
        "{slug}_faq_{instance}_{lang}".format(
            slug=exercise.slug,
            instance=instance.slug,
            lang=lang_code
        ),
        exercise_faq,
        timeout=None
    )
    
    return exercise_faq
    
def regenerate_cache(instance, exercise):    
    for lang_code, _ in settings.LANGUAGES:
        faq_key = "{slug}_faq_{instance}_{lang}".format(
            slug=exercise.slug,
            instance=instance.slug,
            lang=lang_code
        )
        cache.delete(faq_key)
        cache_panel(instance, exercise, lang_code)

def render_panel(request, course, instance, exercise, preopened=[]):
    lang_code = translation.get_language()
    faq_list = cache.get(
        "{slug}_faq_{instance}_{lang}".format(
            slug=exercise.slug,
            instance=instance.slug,
            lang=lang_code
        )
    )
    if not faq_list:
        try:
            faq_list = cache_panel(instance, exercise, lang_code)
        except ValueError:
            return HttpResponseNotFound(_("FAQ for this exercise was not found"))
    
    is_staff = is_course_staff(request.user, instance)
    t = loader.get_template("faq/faq_panel.html")
    c = {
        "course": course,
        "instance": instance,
        "exercise": exercise,
        "editable": is_staff and not instance.frozen,
        "faq_list": faq_list,
        "preopened": preopened
    }
    if is_staff:
        unlinked_questions = FaqQuestion.objects.filter(
            faqtoinstancelink__instance=instance
        ).exclude(faqtoinstancelink__exercise=exercise)
        edit_form = FaqQuestionForm()
        link_form = FaqLinkForm(available_questions=unlinked_questions)
        c["edit_form"] = edit_form
        c["link_form"] = link_form
        
    return t.render(c, request)
        
def clone_faq_links(instance):
    active_links = FaqToInstanceLink.objects.filter(
        instance__course=instance.course,
        revision=None
    ).distinct("question")
    for link in active_links:
        link.id = None
        link.instance=instance
        link.save()
    
    
    

