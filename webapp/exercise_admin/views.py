import collections, json

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseForbidden,\
    HttpResponseNotAllowed, JsonResponse
from django.template import loader
from django.db import transaction, IntegrityError
from django.conf import settings

from reversion import revisions as reversion

# Other needed models
from courses.models import ContentGraph, EmbeddedLink

# The editable models
from courses.models import FileUploadExercise, FileExerciseTest, FileExerciseTestStage,\
    FileExerciseTestCommand, FileExerciseTestExpectedOutput, FileExerciseTestExpectedStdout,\
    FileExerciseTestExpectedStderr, FileExerciseTestIncludeFile
from courses.models import Hint, InstanceIncludeFile, InstanceIncludeFileToExerciseLink
from feedback.models import ContentFeedbackQuestion, TextfieldFeedbackQuestion, \
    ThumbFeedbackQuestion, StarFeedbackQuestion, MultipleChoiceFeedbackQuestion, \
    MultipleChoiceFeedbackAnswer

# Forms
from .forms import CreateFeedbackQuestionForm, CreateFileUploadExerciseForm

def index(request):
    return HttpResponseNotFound()

def save_file_upload_exercise(exercise, form_data, order_hierarchy_json, old_test_ids,
                              old_stage_ids, old_cmd_ids, new_stages, new_commands):
    # Collect the content page data
    e_name = form_data['exercise_name']
    e_content = form_data['exercise_content']
    e_default_points = form_data['exercise_default_points']
    e_tags = [tag for key, tag in sorted(form_data.items()) if key.startswith('exercise_tag')]
    e_feedback_questions = form_data['exercise_feedback_questions']
    e_question = form_data['exercise_question']
    e_manually_evaluated = form_data['exercise_manually_evaluated']
    e_ask_collaborators = form_data['exercise_ask_collaborators']
    e_allowed_filenames = form_data['exercise_allowed_filenames'].split(',') # DEBUG

    exercise.name = e_name
    exercise.content = e_content
    exercise.default_points = e_default_points
    exercise.tags = e_tags
    exercise.feedback_questions = e_feedback_questions
    exercise.question = e_question
    exercise.manually_evaluated = e_manually_evaluated
    exercise.ask_collaborators = e_ask_collaborators
    exercise.allowed_filenames = e_allowed_filenames
    exercise.save()
    
    # Collect the test data
    test_ids = sorted(order_hierarchy_json["stages_of_tests"].keys())
    
    # Check for removed tests (existed before, but not in form data)
    for removed_test_id in sorted(old_test_ids - {int(test_id) for test_id in test_ids if not test_id.startswith('newt')}):
        print("Test with id={} was removed!".format(removed_test_id))
        removed_test = FileExerciseTest.objects.get(id=removed_test_id)
        # TODO: Reversion magic!
        removed_test.delete()
    
    edited_tests = {}
    for test_id in test_ids:
        t_name = form_data['test_{}_name'.format(test_id)]
        
        # Check for new tests
        if test_id.startswith('newt'):
            current_test = FileExerciseTest()
            current_test.exercise = exercise
        else:
            # Check for existing tests that are part of this exercise's suite
            current_test = FileExerciseTest.objects.get(id=int(test_id))

        # Set the test values
        current_test.name = t_name

        # Save the test and store a reference
        current_test.save()
        edited_tests[test_id] = current_test

    # Collect the stage data
    # Deferred constraints: https://code.djangoproject.com/ticket/20581
    for removed_stage_id in sorted(old_stage_ids - {int(stage_id) for stage_id in new_stages.keys() if not stage_id.startswith('news')}):
        print("Stage with id={} was removed!".format(removed_stage_id))
        removed_stage = FileExerciseTestStage.objects.get(id=removed_stage_id)
        # TODO: Reversion magic!
        removed_stage.delete()

    stage_count = len(new_stages)
    edited_stages = {}
    for stage_id, stage_info in new_stages.items():
        s_name = form_data['stage_{}_name'.format(stage_id)]
        s_depends_on = form_data['stage_{}_depends_on'.format(stage_id)]

        if stage_id.startswith('news'):
            current_stage = FileExerciseTestStage()
        else:
            current_stage = FileExerciseTestStage.objects.get(id=int(stage_id))

        current_stage.test = edited_tests[stage_info.test]
        current_stage.name = s_name
        current_stage.depends_on = s_depends_on
        current_stage.ordinal_number = stage_info.ordinal_number + stage_count + 1 # Note

        current_stage.save()
        edited_stages[stage_id] = current_stage

    # HACK: Workaround for lack of deferred constraints on unique_together
    for stage_id, stage_obj in edited_stages.items():
        stage_obj.ordinal_number -= stage_count + 1
        stage_obj.save()
        
    # Collect the command data
    for removed_command_id in sorted(old_cmd_ids - {int(command_id) for command_id in new_commands.keys() if not command_id.startswith('newc')}):
        print("Command with id={} was removed!".format(removed_command_id))
        removed_command = FileExerciseTestCommand.objects.get(id=removed_command_id)
        # TODO: Reversion magic!
        removed_command.delete()

    command_count = len(new_commands)
    edited_commands = {}
    for command_id, command_info in new_commands.items():
        c_command_line = form_data['command_{}_command_line'.format(command_id)]
        c_significant_stdout = form_data['command_{}_significant_stdout'.format(command_id)]
        c_significant_stderr = form_data['command_{}_significant_stderr'.format(command_id)]
        c_input_text = form_data['command_{}_input_text'.format(command_id)]
        c_return_value = form_data['command_{}_return_value'.format(command_id)]
        c_timeout = form_data['command_{}_timeout'.format(command_id)]

        if command_id.startswith('newc'):
            current_command = FileExerciseTestCommand()
        else:
            current_command = FileExerciseTestCommand.objects.get(id=int(command_id))

        current_command.stage = edited_stages[command_info.stage]
        current_command.command_line = c_command_line
        current_command.significant_stdout = c_significant_stdout
        current_command.significant_stderr = c_significant_stderr
        current_command.input_text = c_input_text
        current_command.return_value = c_return_value
        current_command.timeout = c_timeout
        current_command.ordinal_number = command_info.ordinal_number + command_count + 1 # Note

        current_command.save()
        edited_commands[command_id] = current_command

    # HACK: Workaround for lack of deferred constraints on unique_together
    for command_id, command_obj in edited_commands.items():
        command_obj.ordinal_number -= command_count + 1
        command_obj.save()
            
    
        
Stage = collections.namedtuple('Stage', ['test', 'ordinal_number'])
Command = collections.namedtuple('Command', ['stage', 'ordinal_number'])

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
    instance_file_links = InstanceIncludeFileToExerciseLink.objects.filter(exercise=exercise)
    
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
        new_stages = {}
        for test_id, stage_list in order_hierarchy_json['stages_of_tests'].items():
            for i, stage_id in enumerate(stage_list):
                new_stages[stage_id] = Stage(test=test_id, ordinal_number=i+1)

        new_commands = {}
        for stage_id, command_list in order_hierarchy_json['commands_of_stages'].items():
            for i, command_id in enumerate(command_list):
                new_commands[command_id] = Command(stage=stage_id, ordinal_number=i+1)

        old_test_ids = set(tests.values_list('id', flat=True))
        old_stage_ids = set(stages.values_list('id', flat=True))
        old_cmd_ids = set(commands.values_list('id', flat=True))

        data = request.POST.dict()
        data.pop("csrfmiddlewaretoken")
        tag_fields = [k for k in data.keys() if k.startswith("exercise_tag")]

        form = CreateFileUploadExerciseForm(tag_fields, order_hierarchy_json, data)

        if form.is_valid():
            print("DEBUG: the form is valid")
            cleaned_data = form.cleaned_data

            # create/update the form
            try:
                with transaction.atomic():
                    save_file_upload_exercise(exercise, cleaned_data, order_hierarchy_json,
                                              old_test_ids, old_stage_ids, old_cmd_ids,
                                              new_stages, new_commands)
            except IntegrityError as e:
                # TODO: Do something useful
                raise e
            
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
        'instance_file_links': instance_file_links,
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
            choice_keys = sorted([k for (k, v) in cleaned_data.items() if k.startswith(choice_prefix) and v])

            if q_obj.question != question:
                q_obj.question = question
                q_obj.save()
            if q_obj.question_type == "MULTIPLE_CHOICE_FEEDBACK":
                existing_choices = q_obj.get_choices()
                existing_choices_len = len(existing_choices)
                for i, k in enumerate(choice_keys):
                    choice = cleaned_data[k]
                    if existing_choices_len <= i:
                        MultipleChoiceFeedbackAnswer(question=q_obj, answer=choice).save()
                    elif choice not in [choice.answer for choice in existing_choices]:
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
    
    return get_feedback_questions(request)

def get_instance_files(request, exercise):
    if not (request.user.is_staff and request.user.is_authenticated() and request.user.is_active):
        return JsonResponse({
            "error": "Only logged in admins can query feedback questions!"
        })
    
    instance_files = InstanceIncludeFile.objects.all()
    result = []
    
    for instance_file in instance_files:
        try:
            link = InstanceIncludeFileToExerciseLink.objects.get(include_file=instance_file, exercise=exercise)
        except InstanceIncludeFileToExerciseLink.DoesNotExist:
            link = None
        instance_file_json = {
            "default_name": instance_file.default_name,
            "description" : instance_file.description,
            "link" : link,
        }
        result_append(instance_file_json)

    return JsonResponse({
        "result": result
    })
