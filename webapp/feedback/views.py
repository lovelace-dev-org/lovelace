import feedback.models
import courses.models

from django.http import HttpResponseNotFound, HttpResponseNotAllowed, JsonResponse

def content(request, content_slug):
    return HttpResponseNotFound("This page is yet to be implemented")

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

