from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden,\
    HttpResponseNotAllowed
from django.template import loader

from reversion import revisions as reversion

# Other needed models
from courses.models import ContentGraph, EmbeddedLink

# The editable models
from courses.models import FileUploadExercise, FileExerciseTest, FileExerciseTestStage,\
    FileExerciseTestCommand, FileExerciseTestExpectedOutput, FileExerciseTestExpectedStdout,\
    FileExerciseTestExpectedStderr, FileExerciseTestIncludeFile
from courses.models import Hint, InstanceIncludeFile
from feedback.models import TextfieldFeedbackQuestion, ThumbFeedbackQuestion,\
    StarFeedbackQuestion, MultipleChoiceFeedbackQuestion, MultipleChoiceFeedbackAnswer

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
