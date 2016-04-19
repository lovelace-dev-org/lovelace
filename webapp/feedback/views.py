import feedback.models
import courses.models

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseNotAllowed, \
    HttpResponse, JsonResponse
from django.template import loader
from django.db import connection

def textfield_feedback(question, content):
    answers = question.get_answers_by_content(content)
    return {
        "answers" : sorted(set(answers.values_list("answer", "answer_date")), key=lambda a: a[1], reverse=True),
        "answer_count": answers.count(),
        "user_count": len(set(answers.values_list("user")))
    }

def thumb_feedback(question, content):
    answers = question.get_latest_answers_by_content(content)
    user_count = answers.count()
    thumbs_up = list(answers.values_list("thumb_up", flat=True)).count(True)
    thumbs_down = user_count - thumbs_up

    try:
        thumb_up_pct = round((thumbs_up / user_count) * 100, 2)
        thumb_down_pct = round((thumbs_down / user_count) * 100, 2)
    except ZeroDivisionError:
        thumb_up_pct = 0
        thumb_down_pct = 0

    return {
        "thumbs_up": thumbs_up, 
        "thumbs_down": thumbs_down,
        "thumb_up_pct": thumb_up_pct,
        "thumb_down_pct": thumb_down_pct,
        "user_count": user_count
    }

def star_feedback(question, content):
    answers = question.get_latest_answers_by_content(content)
    user_count = answers.count()
    ratings = list(answers.values_list("rating", flat=True))
    rating_counts = [ratings.count(stars) for stars in range(1, 6)]

    rating_pcts = []
    for rcount in rating_counts:
        try:
            rating_pcts.append(round((rcount / user_count) * 100, 2))
        except ZeroDivisionError:
            rating_pcts.append(0.0)

    return {
        "rating_stats" : zip(rating_counts, rating_pcts),
        "user_count" : user_count
    }

def multiple_choice_feedback(question, content):
    choices = list(question.get_choices())
    answers = question.get_latest_answers_by_content(content)
    user_count = answers.count()
    chosen_answers = list(answers.values_list("chosen_answer", flat=True))
    answer_counts = [chosen_answers.count(choice.id) for choice in choices]
        
    answer_pcts = []
    for acount in answer_counts:
        try:
            answer_pcts.append(round((acount / user_count) * 100, 2))
        except ZeroDivisionError:
            answer_pcts.append(0.0)


    return {
        "answer_stats" : zip(choices, answer_counts, answer_pcts),
        "user_count" : user_count
    }

def content_feedback_stats(request, content_slug):
    if not request.user.is_authenticated() and not request.user.is_active and not request.user.is_staff:
        return HttpResponseForbidden("Only logged in admins can view feedback statistics!")
    
    try:
        content = courses.models.ContentPage.objects.get(slug=content_slug)
    except courses.models.ContentPage.DoesNotExist:
        return HttpResponseNotFound("No content page {} found!".format(content_slug))

    questions = content.get_feedback_questions()
    ctx = {
        "content": content,
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
            question_ctx.update(textfield_feedback(question, content))
        elif question_type == "THUMB_FEEDBACK":
            question_ctx.update(thumb_feedback(question, content))
        elif question_type == "STAR_FEEDBACK":
            question_ctx.update(star_feedback(question, content))
        elif question_type == "MULTIPLE_CHOICE_FEEDBACK":
            question_ctx.update(multiple_choice_feedback(question, content))
        stats[question_type.lower()].append(question_ctx)
    ctx["feedback_stats"] = stats
    
    t = loader.get_template("feedback/feedback-stats.html")
    return HttpResponse(t.render(ctx, request))

def receive(request, content_slug, feedback_slug):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not request.user.is_active:
        return JsonResponse({
            "result": "Only logged in users can send feedback!"
        })

    content = courses.models.ContentPage.objects.get(slug=content_slug)
    cfq = feedback.models.ContentFeedbackQuestion.objects.get(slug=feedback_slug)

    user = request.user
    ip = request.META.get("REMOTE_ADDR")
    answer = request.POST

    question = cfq.get_type_object()
    
    try:
        answer_object = question.save_answer(content, user, ip, answer)
    except feedback.models.InvalidFeedbackAnswerException as e:
        return JsonResponse({
            "error": str(e)
        })

    return JsonResponse({
        "result": "Your feedback was received!"
    })

