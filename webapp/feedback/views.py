import feedback.models
import courses.models
from reversion.models import Version

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseNotAllowed, \
    HttpResponseForbidden, JsonResponse
from django.template import loader

from utils.content import first_title_from_content

def textfield_feedback_stats(question, instance, content):
    answers = question.get_answers_by_content(instance, content)
    return {
        "answers" : sorted(set(answers.values_list("answer", "answer_date")), key=lambda a: a[1], reverse=True),
        "answer_count": answers.count(),
        "user_count": len(set(answers.values_list("user")))
    }

def thumb_feedback_stats(question, instance, content):
    answers = question.get_latest_answers_by_content(instance, content)
    user_count = answers.count()
    thumbs_up = list(answers.values_list("thumb_up", flat=True)).count(True)
    thumbs_down = user_count - thumbs_up

    try:
        thumb_up_pct = round((thumbs_up / user_count) * 100, 2)
        thumb_down_pct = round((thumbs_down / user_count) * 100, 2)
    except ZeroDivisionError: # Catch zero division if there are no user answers
        thumb_up_pct = 0
        thumb_down_pct = 0

    return {
        "thumbs_up": thumbs_up, 
        "thumbs_down": thumbs_down,
        "thumb_up_pct": thumb_up_pct,
        "thumb_down_pct": thumb_down_pct,
        "user_count": user_count
    }

def star_feedback_stats(question, instance, content):
    answers = question.get_latest_answers_by_content(instance, content)
    user_count = answers.count()
    ratings = list(answers.values_list("rating", flat=True))
    rating_counts = [ratings.count(stars) for stars in range(1, 6)]

    rating_pcts = []
    for rcount in rating_counts:
        try:
            rating_pcts.append(round((rcount / user_count) * 100, 2))
        except ZeroDivisionError: # Catch zero division if there are no user answers
            rating_pcts.append(0.0)

    return {
        "rating_stats" : zip(rating_counts, rating_pcts),
        "user_count" : user_count
    }

def multiple_choice_feedback_stats(question, instance, content):
    choices = list(question.get_choices())
    answers = question.get_latest_answers_by_content(instance, content)
    user_count = answers.count()
    chosen_answers = list(answers.values_list("chosen_answer", flat=True))
    answer_counts = [chosen_answers.count(choice.id) for choice in choices]
        
    answer_pcts = []
    for ans_count in answer_counts:
        try:
            answer_pcts.append(round((ans_count / user_count) * 100, 2))
        except ZeroDivisionError: # Catch zero division if there are no user answers
            answer_pcts.append(0.0)

    return {
        "answer_stats" : zip(choices, answer_counts, answer_pcts),
        "user_count" : user_count
    }

def content_feedback_stats(request, instance, content):
    if not request.user.is_authenticated or not request.user.is_active or not request.user.is_staff:
        return HttpResponseForbidden("Only logged in admins can view feedback statistics!")
    
    links = courses.models.EmbeddedLink.objects.filter(embedded_page=content, instance=instance)
    if links:
        link = links.first()
        if links.count() == 1:
            single_linked = True
            parent = link.parent
        else:
            single_linked = False
            parent = None
        embedded = True
    else:
        try:
            link = courses.models.ContentGraph.objects.get(instance=instance, content=content)
            parent = None
            single_linked = True
            embedded = False
        except courses.models.ContentGraph.DoesNotExist:
            return HttpResponseNotFound("Content {} is not linked to course instance {}".format(content_slug, instance_slug))

    if link.revision is None:        
        pass
    else:
        try:
            content = Version.objects.get_for_object(content).get(revision=link.revision)\
                                                         ._object_version.object
        except Version.DoesNotExist as e:
            return HttpResponseNotFound("The requested revision for {} is not available".format(content.slug))
        
    title, anchor = first_title_from_content(content.content)
    
    questions = content.get_feedback_questions()
    ctx = {
        "content": content,
        "parent": parent,
        "instance": instance,
        "course": instance.course,
        "instance_slug": instance.slug,
        "instance_name": instance.name,
        "course_slug": instance.course.slug,
        "course_name": instance.course.name,
        "single_linked": single_linked,
        "anchor": anchor,
        "tasktype": content.get_human_readable_type(),
    }

    stats = {
        "textfield_feedback": [],
        "thumb_feedback" : [],
        "star_feedback" : [],
        "multiple_choice_feedback" : []
    }
    for question in questions:
        question_type = question.question_type
        question_ctx = {
            "question": question.question,
            "question_type": question_type,
            "question_slug": question.slug,
        }
        if question_type == "TEXTFIELD_FEEDBACK":
            question_ctx.update(textfield_feedback_stats(question, instance, content))
        elif question_type == "THUMB_FEEDBACK":
            question_ctx.update(thumb_feedback_stats(question, instance, content))
        elif question_type == "STAR_FEEDBACK":
            question_ctx.update(star_feedback_stats(question, instance, content))
        elif question_type == "MULTIPLE_CHOICE_FEEDBACK":
            question_ctx.update(multiple_choice_feedback_stats(question, instance, content))
        stats[question_type.lower()].append(question_ctx)
    ctx["feedback_stats"] = stats

    
    t = loader.get_template("feedback/feedback-stats.html")
    return HttpResponse(t.render(ctx, request))

def receive(request, instance, content, question):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not request.user.is_active:
        return JsonResponse({
            "result": "Only logged in users can send feedback!"
        })

    #TODO: Check that the user has successfully enrolled to the course instance.
    #TODO: Take the revision into account.
    
    user = request.user
    ip = request.META.get("REMOTE_ADDR")
    answer = request.POST

    question = question.get_type_object()
    
    try:
        answer_object = question.save_answer(instance, content, user, ip, answer)
    except feedback.models.InvalidFeedbackAnswerException as e:
        return JsonResponse({
            "error": str(e)
        })

    return JsonResponse({
        "result": "Your feedback was received!"
    })

