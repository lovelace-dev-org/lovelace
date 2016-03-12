import feedback.models
import courses.models

from django.http import HttpResponseNotFound, HttpResponseNotAllowed, JsonResponse

def textfield_feedback(question):
    answers = question.get_answers_by_content(question)
    return {
        "answers" : set(answers.values_list("answer", flat=True)),
        "answer_count": answers.count()
    }

def thumb_feedback(question):
    answers = question.get_latest_answers_by_content(question)
    answer_count = answers.count()
    thumb_ups = answers.values_list("thumb_up", flat=True).count(True)
    thumb_downs = answer_count - thumb_ups

    try:
        thumb_up_pct = round((thumb_ups / answer_count) * 100, 2)
        thumb_down_pct = round((thumb_downs / answer_count) * 100, 2)
    except ZeroDivisionError:
        thumb_up_pct = 0
        thumb_down_pct = 0

    return {
        "thumb_ups": thumb_ups, 
        "thumb_downs": thumb_downs,
        "thumb_up_pct": thumb_up_pct,
        "thumb_down_pct": thumb_down_pct,
        "answer_count": answer_count
    }

def star_feedback(question):
    answers = question.get_latest_answers_by_content(question)
    answer_count = answers.count()
    ratings = answers.values_list("ratings", flat=True)
    rating_counts = [ratings.count(stars) for stars in range(1, 6)]
    try:
        rating_pcts = [round((rcount / answer_count) * 100, 2) for rcount in rating_counts]
    except ZeroDivisionError:
        rating_pcts = [0] * 5

    return {
        "rating_counts" : rating_counts,
        "rating_pcts" : rating_pcts,
        "answer_count" : answer_count
    }

def content(request, content_slug):
    if not request.user.is_authenticated() and not request.user.is_active and not request.user.is_staff:
        return HttpResponseNotFound("Only logged in admins can view feedback statistics!")
    
    try:
        content = courses.models.ContentPage.objects.get(slug=content_slug)
    except courses.models.ContentPage.DoesNotExist:
        return HttpResponseNotFound("No content page {} found!".format(content_slug))
    
    questions = content.get_feedback_questions()
    ctx = {
        "content": content,
        "tasktype": content.get_human_readable_type(),
    }

    feedback_stats = []
    for question in questions:
        question_type = question.question_type
        question_ctx = {
            "question": question.question,
            "question_type": question_type,
        }
        if question_type == "TEXTFIELD_FEEDBACK":
            question_ctx.update(textfield_feedback(question))
        elif question_type == "THUMB_FEEDBACK":
            question_ctx.update(thumb_feedback(question))
        elif question_type == "STAR_FEEDBACK":
            question_ctx.update(star_feedback(question))

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

