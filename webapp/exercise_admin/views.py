import json

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden,\
    HttpResponseNotAllowed, JsonResponse
from django.template import loader
from django.db import transaction

from reversion import revisions as reversion

# Other needed models
from courses.models import ContentGraph, EmbeddedLink

# The editable models
from courses.models import FileUploadExercise, FileExerciseTest, FileExerciseTestStage,\
    FileExerciseTestCommand, FileExerciseTestExpectedOutput, FileExerciseTestExpectedStdout,\
    FileExerciseTestExpectedStderr, FileExerciseTestIncludeFile
from courses.models import Hint, InstanceIncludeFile
from feedback.models import ContentFeedbackQuestion, TextfieldFeedbackQuestion, \
    ThumbFeedbackQuestion, StarFeedbackQuestion, MultipleChoiceFeedbackQuestion, \
    MultipleChoiceFeedbackAnswer

# Forms
from .forms import CreateFeedbackQuestionForm, CreateFileUploadExerciseForm

def index(request):
    return HttpResponse('to be created')

# We need the following urls, at least:
# fileuploadexercise/add
# fileuploadexercise/{id}/change
# fileuploadexercise/{id}/delete
def file_upload_exercise(request, exercise_id=None, action=None):
    # Admins only, consider @staff_member_required
    if not (request.user.is_staff and request.user.is_authenticated() and request.user.is_active):
        return HttpResponseForbidden("Only admins are allowed to edit file upload exercises.")

    # GET = show the page
    # POST = validate & save the submitted form


    # TODO: ”Create” buttons for new tests, stages, commands etc.

    # TODO: All that stuff in admin which allows the user to upload new things etc.

    # TODO: Rethink models.py.

    # TODO: How to handle the creation of new exercises? 

    # Get the exercise
    try:
        exercise = FileUploadExercise.objects.get(id=exercise_id)
    except FileUploadExercise.DoesNotExist as e:
        #pass # DEBUG
        return HttpResponseNotFound("File upload exercise with id={} not found.".format(exercise_id))

    # Get the configurable hints linked to this exercise
    hints = Hint.objects.filter(exercise=exercise)

    # Get the exercise specific files
    include_files = FileExerciseTestIncludeFile.objects.filter(exercise=exercise)
    
    # TODO: Get the instance specific files
    # 1. scan the content graphs and embedded links to find out, if this exercise is linked
    #    to an instance. we need a manytomany relation here, that is instance specific
    # 2. get the files and show a pool of them
    instance_files = InstanceIncludeFile.objects.all() # TODO: This is debug code
    
    tests = FileExerciseTest.objects.filter(exercise=exercise_id).order_by("name")
    test_list = []
    for test in tests:
        stages = FileExerciseTestStage.objects.filter(test=test).order_by("ordinal_number")
        stage_list = []
        for stage in stages:
            cmd_list = []
            commands = FileExerciseTestCommand.objects.filter(stage=stage).order_by("ordinal_number")
            for cmd in commands:
                expected_outputs = FileExerciseTestExpectedOutput.objects.filter(command=cmd).order_by("ordinal_number")
                cmd_list.append((cmd, expected_outputs))
            stage_list.append((stage, cmd_list))
        test_list.append((test, stage_list))
    
    # TODO: Remember the manual versioning!
    # Save creates new versions, but the version history can also be browsed read-only.
    # https://django-reversion.readthedocs.io/en/latest/api.html#creating-revisions

    # TODO: Remember the translations!
    # http://django-modeltranslation.readthedocs.io/en/latest/usage.html

    # TODO: Save the additions, removals and editions sent by the user 
    if request.method == "POST":
        form_contents = request.POST
        uploaded_files = request.FILES

        #print(form_contents)
        print("POST key-value pairs:")
        for k, v in sorted(form_contents.items()):
            if k == "order_hierarchy":
                order_hierarchy_json = json.loads(v)
                print("order_hierarchy:")
                print(json.dumps(order_hierarchy_json, indent=4))
            else:
                print("{}: '{}'".format(k, v))

        print(uploaded_files)

        data = request.POST.dict()
        data.pop("csrfmiddlewaretoken")
        tag_count = len([k for k in data.keys() if k.startswith("exercise_tag")])

        form = CreateFileUploadExerciseForm(tag_count, order_hierarchy_json, data)

        if form.is_valid():
            print("DEBUG: the form is valid")
            # create/update the form
            with transaction.atomic():
                pass

            return JsonResponse({
                "yeah!": "everything went ok",
            })
        else:
            print("DEBUG: the form is not valid")
            print(form.errors)
            return JsonResponse({
                "error": form.errors,
            })
    
    # TODO: Modify the admin site to direct file upload exercise edit urls here instead.
    # ...or maybe modify the urls?
    
    t = loader.get_template("exercise_admin/file-upload-exercise-{action}.html".format(action=action))
    c = {
        'exercise': exercise,
        'hints': hints,
        'include_files': include_files,
        'instance_files': instance_files,
        'tests': test_list,

    }
    return HttpResponse(t.render(c, request))

def get_feedback_questions(request):
    if not (request.user.is_staff and request.user.is_authenticated() and request.user.is_active):
        return JsonResponse({
            "error": "Only logged in admins can query feedback questions!"
        })

    feedback_questions = ContentFeedbackQuestion.objects.all()
    result = []
    for question in feedback_questions:
        question = question.get_type_object()
        question_json = {
            "id": question.id,
            "question" : question.question,
            "type" : question.question_type,
            "readable_type": question.get_human_readable_type(),
            "choices": [],
        }
        if question.question_type == "MULTIPLE_CHOICE_FEEDBACK":
            question_json["choices"] = [choice.answer for choice in question.get_choices()]
        result.append(question_json)
    
    return JsonResponse({
        "result": result
    })

def edit_feedback_questions(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not (request.user.is_staff and request.user.is_authenticated() and request.user.is_active):
        return JsonResponse({
            "error" : {
                "__all__" : {
                    "message" : "Only logged in users can create feedback questions!",
                    "code" : "authentication"
                }
            }
        })

    data = request.POST.dict()
    data.pop("csrfmiddlewaretoken")

    feedback_questions = ContentFeedbackQuestion.objects.all()
    form = CreateFeedbackQuestionForm(feedback_questions, data)
    
    if form.is_valid():
        # Edit existing feedback questions if necessary
        cleaned_data = form.cleaned_data
        for q_obj in feedback_questions:
            q_obj = q_obj.get_type_object()
            question = cleaned_data["question_field_[{}]".format(q_obj.id)]
            choice_prefix = "choice_field_[{}]".format(q_obj.id)
            choices = [v for (k, v) in cleaned_data.items() if k.startswith(choice_prefix) and v]

            if q_obj.question != question:
                q_obj.question = question
                q_obj.save()
            if q_obj.question_type == "MULTIPLE_CHOICE_FEEDBACK":
                existing_choices = q_obj.get_choices()
                existing_choices_len = len(existing_choices)
                for i, choice in enumerate(choices):
                    if existing_choices_len <= i:
                        MultipleChoiceFeedbackAnswer(question=q_obj, answer=choice).save()                        
                    elif existing_choices[i] != choice:
                        choice_obj = existing_choices[i]
                        choice_obj.answer = choice
                        choice_obj.save()
                        
        # Add new feedback questions
        new_feedback_count = len([k for k in cleaned_data if k.startswith("question_field_[new")])
        for i in range(new_feedback_count):
            id_new = "new-{}".format(i + 1)
            question = cleaned_data["question_field_[{}]".format(id_new)]
            question_type = cleaned_data["type_field_[{}]".format(id_new)]
            choice_prefix = "choice_field_[{}]".format(id_new)
            choices = [v for (k, v) in cleaned_data.items() if k.startswith(choice_prefix) and v]
            
            if question_type == "THUMB_FEEDBACK":
                q_obj = ThumbFeedbackQuestion(question=question)
                q_obj.save()
            elif question_type == "STAR_FEEDBACK":
                q_obj = StarFeedbackQuestion(question=question)
                q_obj.save()
            elif question_type == "MULTIPLE_CHOICE_FEEDBACK":
                q_obj = MultipleChoiceFeedbackQuestion(question=question)
                q_obj.save()
                for choice in choices:
                    MultipleChoiceFeedbackAnswer(question=q_obj, answer=choice).save()
            elif question_type == "TEXTFIELD_FEEDBACK":
                q_obj = TextfieldFeedbackQuestion(question=question)
                q_obj.save()
    else:
        return JsonResponse({
            "error" : form.errors
        })
    
    return JsonResponse({
        "result" : {
            "question" : question,
            "id" : q_obj.id,
            "type" : q_obj.get_human_readable_type(),
            "choices" : choices,
        }
    })
