import collections
import json
import logging
import os

from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.template import loader
from django.db import transaction, IntegrityError
from django.conf import settings
from django.urls import reverse  # Django 1.10
from django.core import serializers
from django.utils.translation import gettext as _

# from django.core.urlresolvers import reverse # Django 1.9

from reversion import revisions as reversion

# Other needed models

# The editable models
from courses.models import (
    Course,
    ContentPage,
    FileUploadExercise,
    FileExerciseSettings,
    FileExerciseTest,
    FileExerciseTestStage,
    FileExerciseTestCommand,
    FileExerciseTestExpectedOutput,
    FileExerciseTestIncludeFile,
    IncludeFileSettings,
    Hint,
    InstanceIncludeFile,
    InstanceIncludeFileToExerciseLink,
)
from feedback.models import (
    ContentFeedbackQuestion,
    TextfieldFeedbackQuestion,
    ThumbFeedbackQuestion,
    StarFeedbackQuestion,
    MultipleChoiceFeedbackQuestion,
    MultipleChoiceFeedbackAnswer,
)
from utils.access import determine_access
from utils.files import generate_download_response

# Forms
from .forms import (
    CreateFeedbackQuestionsForm,
    CreateInstanceIncludeFilesForm,
    CreateFileUploadExerciseForm,
)
from .utils import get_default_lang, get_lang_list


logger = logging.getLogger(__name__)

def index(request):
    return HttpResponseNotFound()


def convert_object_to_json(obj):
    return json.loads(serializers.serialize("json", [obj]))[0]


def convert_new_objects_to_json(objs):
    return {
        old_id: convert_object_to_json(obj)
        for (old_id, obj) in objs.items()
        if old_id.startswith("new")
    }


def save_file_upload_exercise(
    exercise,
    form_data,
    order_hierarchy_json,
    old_hint_ids,
    old_ef_ids,
    old_if_ids,
    old_test_ids,
    old_stage_ids,
    old_cmd_ids,
    new_stages,
    new_commands,
    hint_ids,
    ef_ids,
    if_ids,
):
    deletions = []
    # Collect the content page data
    # e_name = form_data['exercise_name']
    # e_content = form_data['exercise_content']
    e_default_points = form_data["exercise_default_points"]
    e_evaluation_group = form_data["exercise_evaluation_group"]
    e_tags = [tag for key, tag in sorted(form_data.items()) if key.startswith("exercise_tag")]
    e_feedback_questions = form_data.get("exercise_feedback_questions") or []
    # e_question = form_data['exercise_question']
    e_group_submission = form_data["exercise_group_submission"]
    e_manually_evaluated = form_data["exercise_manually_evaluated"]
    e_ask_collaborators = form_data["exercise_ask_collaborators"]
    e_allowed_filenames = form_data["exercise_allowed_filenames"]
    e_max_file_count = form_data["exercise_max_file_count"]
    e_answer_mode = form_data["exercise_answer_mode"]

    lang_list = get_lang_list()
    for lang_code, _ in lang_list:
        e_name = form_data[f"exercise_name_{lang_code}"]
        setattr(exercise, f"name_{lang_code}", e_name)

        e_content = form_data[f"exercise_content_{lang_code}"]
        setattr(exercise, f"content_{lang_code}", e_content)

        e_question = form_data[f"exercise_question_{lang_code}"]
        setattr(exercise, f"question_{lang_code}", e_question)

    # exercise.name = e_name
    # exercise.content = e_content
    exercise.default_points = e_default_points
    exercise.evaluation_group = e_evaluation_group
    exercise.tags = e_tags
    # exercise.question = e_question
    exercise.group_submission = e_group_submission
    exercise.manually_evaluated = e_manually_evaluated
    exercise.ask_collaborators = e_ask_collaborators
    exercise.save()
    # save() first so that m2m can be used (when adding a new exercise)
    exercise.feedback_questions.set(e_feedback_questions)
    exercise.save()

    extra_settings = exercise.fileexercisesettings
    extra_settings.allowed_filenames = e_allowed_filenames
    extra_settings.max_file_count = e_max_file_count
    extra_settings.answer_mode = e_answer_mode

    for lang_code, _ in lang_list:
        e_answer_filename = form_data[f"exercise_answer_filename_{lang_code}"]
        setattr(extra_settings, f"answer_filename_{lang_code}", e_answer_filename)

    extra_settings.save()

    # Hints

    for removed_hint_id in sorted(
        old_hint_ids - {int(hint_id) for hint_id in hint_ids if not hint_id.startswith("new-")}
    ):
        removed_hint = Hint.objects.get(id=removed_hint_id)
        deletion = removed_hint.delete()
        deletions.append(deletion)

    edited_hints = {}
    for hint_id in hint_ids:
        if hint_id.startswith("new-"):
            current_hint = Hint()
            current_hint.exercise = exercise
        else:
            current_hint = Hint.objects.get(id=int(hint_id))

        for lang_code, _ in lang_list:
            h_content = form_data[f"hint_content_[{hint_id}]_{lang_code}"]
            setattr(current_hint, f"hint_{lang_code}", h_content)

        current_hint.tries_to_unlock = form_data[f"hint_tries_[{hint_id}]"]
        current_hint.save()
        edited_hints[hint_id] = current_hint

    # Exercise included files

    for removed_ef_id in sorted(
        old_ef_ids - {int(ef_id) for ef_id in ef_ids if not ef_id.startswith("new")}
    ):
        removed_ef = FileExerciseTestIncludeFile.objects.filter(id=removed_ef_id)
        deletion = removed_ef.delete()
        deletions.append(deletion)

    edited_exercise_files = {}
    for ef_id in ef_ids:
        if ef_id.startswith("new"):
            current_ef = FileExerciseTestIncludeFile()
            current_ef.exercise = exercise
            ef_settings = IncludeFileSettings()
            current_ef.file_settings = ef_settings
        else:
            current_ef = FileExerciseTestIncludeFile.objects.get(id=int(ef_id))

        for lang_code, _ in lang_list:
            ef_default_name = form_data[f"included_file_default_name_[{ef_id}]_{lang_code}"]
            ef_description = form_data[f"included_file_description_[{ef_id}]_{lang_code}"]
            ef_name = form_data[f"included_file_name_[{ef_id}]_{lang_code}"]
            ef_fileinfo = form_data[f"included_file_[{ef_id}]_{lang_code}"]
            setattr(current_ef, f"default_name_{lang_code}", ef_default_name)
            setattr(current_ef, f"description_{lang_code}", ef_description)
            setattr(current_ef.file_settings, f"name_{lang_code}", ef_name)
            if ef_fileinfo is not None:
                setattr(current_ef, f"fileinfo_{lang_code}", ef_fileinfo)

        current_ef.file_settings.purpose = form_data[f"included_file_purpose_[{ef_id}]"]
        current_ef.file_settings.chown_settings = form_data[f"included_file_chown_[{ef_id}]"]
        current_ef.file_settings.chgrp_settings = form_data[f"included_file_chgrp_[{ef_id}]"]
        current_ef.file_settings.chmod_settings = form_data[f"included_file_chmod_[{ef_id}]"]

        current_ef.file_settings.save()
        current_ef.file_settings = (
            current_ef.file_settings
        )  # Otherwise 'file_settings_id' doesn't exist :P
        current_ef.save()

        edited_exercise_files[ef_id] = current_ef

    for removed_if_link_id in sorted(
        old_if_ids - {if_id for if_id in if_ids if not if_id.startswith("new")}
    ):
        # removed_if_link = InstanceIncludeFileToExerciseLink.objects.f
        removed_if_link = InstanceIncludeFileToExerciseLink.objects.filter(
            include_file=removed_if_link_id, exercise=exercise
        )
        deletion = removed_if_link.delete()
        deletions.append(deletion)

    edited_instance_file_links = {}
    for if_id in if_ids:
        if if_id not in old_if_ids:
            current_if_link = InstanceIncludeFileToExerciseLink()
            current_if_link.exercise = exercise
            current_if_link.include_file = InstanceIncludeFile.objects.get(id=if_id)
            if_settings = IncludeFileSettings()
            current_if_link.file_settings = if_settings
        else:
            current_if_link = InstanceIncludeFileToExerciseLink.objects.filter(
                include_file=int(if_id), exercise=exercise
            )[0]

        for lang_code, _ in lang_list:
            if_name = form_data[f"instance_file_name_[{if_id}]_{lang_code}"]
            setattr(current_if_link.file_settings, f"name_{lang_code}", if_name)

        current_if_link.file_settings.purpose = form_data[f"instance_file_purpose_[{if_id}]"]
        current_if_link.file_settings.chown_settings = form_data[f"instance_file_chown_[{if_id}]"]
        current_if_link.file_settings.chgrp_settings = form_data[f"instance_file_chgrp_[{if_id}]"]
        current_if_link.file_settings.chmod_settings = form_data[f"instance_file_chmod_[{if_id}]"]

        current_if_link.file_settings.save()
        current_if_link.file_settings = current_if_link.file_settings
        current_if_link.save()

        edited_instance_file_links[if_id] = current_if_link

    # Collect the test data
    test_ids = sorted(order_hierarchy_json["stages_of_tests"].keys())

    # Check for removed tests (existed before, but not in form data)
    for removed_test_id in sorted(
        old_test_ids - {int(test_id) for test_id in test_ids if not test_id.startswith("newt")}
    ):
        removed_test = FileExerciseTest.objects.get(id=removed_test_id)
        deletion = removed_test.delete()
        deletions.append(deletion)

    edited_tests = {}
    for test_id in test_ids:
        t_name = form_data[f"test_{test_id}_name"]
        required_files = [i.split("_") for i in form_data[f"test_{test_id}_required_files"]]
        t_required_ef = [edited_exercise_files[i[1]] for i in required_files if i[0] == "ef"]
        t_required_if = [int(i[1]) for i in required_files if i[0] == "if" and i[1] in if_ids]

        # Check for new tests
        if test_id.startswith("newt"):
            current_test = FileExerciseTest()
            current_test.exercise = exercise
        else:
            # Check for existing tests that are part of this exercise's suite
            current_test = FileExerciseTest.objects.get(id=int(test_id))

        # Set the test values
        current_test.name = t_name
        current_test.save()  # Needed for the required files
        current_test.required_files.set(t_required_ef)
        current_test.required_instance_files.set(t_required_if)

        # Save the test and store a reference
        current_test.save()
        edited_tests[test_id] = current_test

    # Collect the stage data
    # Deferred constraints: https://code.djangoproject.com/ticket/20581
    for removed_stage_id in sorted(
        old_stage_ids
        - {int(stage_id) for stage_id in new_stages.keys() if not stage_id.startswith("news")}
    ):
        try:
            removed_stage = FileExerciseTestStage.objects.get(id=removed_stage_id)
        except FileExerciseTestStage.DoesNotExist:
            pass  # Probably taken care of by test deletion cascade
        else:
            deletion = removed_stage.delete()
            deletions.append(deletion)

    stage_count = len(new_stages)
    edited_stages = {}
    for stage_id, stage_info in new_stages.items():
        s_depends_on = form_data[f"stage_{stage_id}_depends_on"]

        if stage_id.startswith("news"):
            current_stage = FileExerciseTestStage()
        else:
            current_stage = FileExerciseTestStage.objects.get(id=int(stage_id))

        for lang_code, _ in lang_list:
            s_name = form_data[f"stage_{stage_id}_name_{lang_code}"]
            setattr(current_stage, "name_{lang_code}", s_name)

        current_stage.test = edited_tests[stage_info.test]
        current_stage.depends_on = s_depends_on
        current_stage.ordinal_number = stage_info.ordinal_number + stage_count + 1  # Note

        current_stage.save()
        edited_stages[stage_id] = current_stage

    # HACK: Workaround for lack of deferred constraints on unique_together
    for stage_id, stage_obj in edited_stages.items():
        stage_obj.ordinal_number -= stage_count + 1
        stage_obj.save()

    # Collect the command data
    for removed_command_id in sorted(
        old_cmd_ids
        - {
            int(command_id)
            for command_id in new_commands.keys()
            if not command_id.startswith("newc")
        }
    ):
        try:
            removed_command = FileExerciseTestCommand.objects.get(id=removed_command_id)
        except FileExerciseTestCommand.DoesNotExist:
            pass  # Probably taken care of by test or stage deletion cascade
        else:
            deletion = removed_command.delete()
            deletions.append(deletion)

    command_count = len(new_commands)
    edited_commands = {}
    for command_id, command_info in new_commands.items():
        c_significant_stdout = form_data[f"command_{command_id}_significant_stdout"]
        c_significant_stderr = form_data[f"command_{command_id}_significant_stderr"]
        c_json_output = form_data[f"command_{command_id}_json_output"]
        c_return_value = form_data[f"command_{command_id}_return_value"]
        c_timeout = form_data[f"command_{command_id}_timeout"]

        if command_id.startswith("newc"):
            current_command = FileExerciseTestCommand()
        else:
            current_command = FileExerciseTestCommand.objects.get(id=int(command_id))

        for lang_code, _ in lang_list:
            c_command_line = form_data[f"command_{command_id}_command_line_{lang_code}"]
            c_input_text = form_data[f"command_{command_id}_input_text_{lang_code}"]
            setattr(current_command, f"command_line_{lang_code}", c_command_line)
            setattr(current_command, f"input_text_{lang_code}", c_input_text)

        current_command.stage = edited_stages[command_info.stage]
        current_command.significant_stdout = c_significant_stdout
        current_command.significant_stderr = c_significant_stderr
        current_command.json_output = c_json_output
        current_command.return_value = c_return_value
        current_command.timeout = c_timeout
        current_command.ordinal_number = command_info.ordinal_number + command_count + 1  # Note

        current_command.save()
        edited_commands[command_id] = current_command

    # HACK: Workaround for lack of deferred constraints on unique_together
    for command_id, command_obj in edited_commands.items():
        command_obj.ordinal_number -= command_count + 1
        command_obj.save()

    return {
        "hints": convert_new_objects_to_json(edited_hints),
        "included_files": convert_new_objects_to_json(edited_exercise_files),
        "tests": convert_new_objects_to_json(edited_tests),
        "stages": convert_new_objects_to_json(edited_stages),
        "commands": convert_new_objects_to_json(edited_commands),
    }


Stage = collections.namedtuple("Stage", ["test", "ordinal_number"])
Command = collections.namedtuple("Command", ["stage", "ordinal_number"])


# We need the following urls, at least:
# fileuploadexercise/add
# fileuploadexercise/{id}/change
def file_upload_exercise(request, exercise_id=None, action=None):
    # Admins only, consider @staff_member_required
    if not (request.user.is_staff and request.user.is_authenticated and request.user.is_active):
        return HttpResponseForbidden("Only admins are allowed to edit file upload exercises.")

    # GET = show the page
    # POST = validate & save the submitted form

    if action == "add":
        # Handle the creation of new exercises
        add_or_edit = "Add"

        if request.method == "GET":
            # The user requested the edit page for adding new exercises
            lang_list = get_lang_list()

            class FakeExercise:
                id = "new-exercise"
                slug = None

                def __init__(self):
                    for lang_code, _ in lang_list:
                        setattr(self, f"name_{lang_code}", "")
                        setattr(self, f"content_{lang_code}", "")
                        setattr(self, f"question_{lang_code}", "")

            exercise = FakeExercise()
        elif request.method == "POST":
            # The user requested to save a new exercise
            exercise = FileUploadExercise()
        hints = []
        include_files = []
        instance_file_links = []
        tests = []
        test_list = []
        stages = None
        commands = None
        stage_list = []
        cmd_list = []
    elif action == "change":
        add_or_edit = "Edit"
        # Get the exercise
        try:
            exercise = FileUploadExercise.objects.get(id=exercise_id)
        except FileUploadExercise.DoesNotExist as e:
            return HttpResponseNotFound(f"File upload exercise with id={exercise_id} not found.")

        # Get the configurable hints linked to this exercise
        hints = Hint.objects.filter(exercise=exercise)

        # Get the exercise specific files
        include_files = FileExerciseTestIncludeFile.objects.filter(exercise=exercise)

        # Get the instance specific file links
        instance_file_links = InstanceIncludeFileToExerciseLink.objects.filter(exercise=exercise)

        tests = FileExerciseTest.objects.filter(exercise=exercise_id).order_by("name")
        test_list = []
        stages = None
        commands = None
        for test in tests:
            stages = FileExerciseTestStage.objects.filter(test=test).order_by("ordinal_number")
            stage_list = []
            for stage in stages:
                cmd_list = []
                commands = FileExerciseTestCommand.objects.filter(stage=stage).order_by(
                    "ordinal_number"
                )
                for cmd in commands:
                    expected_outputs = FileExerciseTestExpectedOutput.objects.filter(command=cmd)
                    cmd_list.append((cmd, expected_outputs))
                stage_list.append((stage, cmd_list))
            test_list.append((test, stage_list))
    else:
        return HttpResponse(content="400 Bad request", status=400)

    instance_files = InstanceIncludeFile.objects.all()
    instance_files_linked = [link.include_file for link in instance_file_links]
    instance_files_not_linked = [f for f in instance_files if f not in instance_files_linked]
    instances = Course.objects.all().order_by("name")

    if request.method == "POST":
        form_contents = request.POST
        files = request.FILES

        for k, v in sorted(form_contents.lists()):
            if k == "order_hierarchy":
                order_hierarchy_json = json.loads(v[0])
                logger.debug("order_hierarchy:")
                logger.debug(json.dumps(order_hierarchy_json, indent=4))
            else:
                logger.debug(f"{k}: '{v}'")

        new_stages = {}
        for test_id, stage_list in order_hierarchy_json["stages_of_tests"].items():
            for i, stage_id in enumerate(stage_list):
                new_stages[stage_id] = Stage(test=test_id, ordinal_number=i + 1)

        new_commands = {}
        for stage_id, command_list in order_hierarchy_json["commands_of_stages"].items():
            for i, command_id in enumerate(command_list):
                new_commands[command_id] = Command(stage=stage_id, ordinal_number=i + 1)

        old_hint_ids = set(hints.values_list("id", flat=True)) if action == "change" else set()
        old_ef_ids = (
            set(include_files.values_list("id", flat=True)) if action == "change" else set()
        )
        old_if_ids = (
            set(
                str(old_id) for old_id in instance_file_links.values_list("include_file", flat=True)
            )
            if action == "change"
            else set()
        )
        old_test_ids = set(tests.values_list("id", flat=True)) if action == "change" else set()
        if stages is not None:
            old_stage_ids = (
                set(stages.values_list("id", flat=True)) if action == "change" else set()
            )
        else:
            old_stage_ids = set()
        if commands is not None:
            old_cmd_ids = (
                set(commands.values_list("id", flat=True)) if action == "change" else set()
            )
        else:
            old_cmd_ids = set()

        data = request.POST.copy()
        data.pop("csrfmiddlewaretoken")
        tag_fields = [k for k in data.keys() if k.startswith("exercise_tag")]
        hint_ids = [k.split("_")[2][1:-1] for k in data.keys() if k.startswith("hint_tries")]
        ef_ids = {k.split("_")[3][1:-1] for k in data.keys() if k.startswith("included_file_name")}
        if_ids = {
            k.split("_")[3][1:-1] for k in data.keys() if k.startswith("instance_file_purpose")
        }

        form = CreateFileUploadExerciseForm(
            tag_fields, hint_ids, ef_ids, if_ids, order_hierarchy_json, data, files
        )

        if not form.is_valid():
            return JsonResponse(
                status=400,
                data={
                    "errors": form.errors,
                },
            )

        cleaned_data = form.cleaned_data

        # create/update the form
        try:
            with transaction.atomic(), reversion.create_revision():
                new_objects = save_file_upload_exercise(
                    exercise,
                    cleaned_data,
                    order_hierarchy_json,
                    old_hint_ids,
                    old_ef_ids,
                    old_if_ids,
                    old_test_ids,
                    old_stage_ids,
                    old_cmd_ids,
                    new_stages,
                    new_commands,
                    hint_ids,
                    ef_ids,
                    if_ids,
                )
                reversion.set_user(request.user)
                reversion.set_comment(cleaned_data["version_comment"])
        except IntegrityError as e:
            raise e

        if action == "add":
            redirect_url = reverse(
                "exercise_admin:file_upload_change",
                kwargs={"exercise_id": exercise.id, "action": "change"},
            )
        else:
            redirect_url = ""

        return JsonResponse(
            {
                "yeah!": "everything went ok",
                "redirect_url": redirect_url,
                "new_objects": new_objects,
            }
        )

    t = loader.get_template("exercise_admin/file-upload-exercise-change.html")
    c = {
        "add_or_edit": add_or_edit,
        "answer_mode_choices": FileExerciseSettings.ANSWER_MODE_CHOICES,
        "exercise": exercise,
        "hints": hints,
        "instances": instances,
        "include_files": include_files,
        "instance_files": instance_files,
        "instance_files_not_linked": instance_files_not_linked,
        "instance_file_links": instance_file_links,
        "tests": test_list,
    }
    return HttpResponse(t.render(c, request))


def get_feedback_questions(request):
    if not (request.user.is_staff and request.user.is_authenticated and request.user.is_active):
        return JsonResponse({"error": "Only logged in admins can query feedback questions!"})

    feedback_questions = ContentFeedbackQuestion.objects.all()
    lang_list = get_lang_list()
    result = []

    for question in feedback_questions:
        question = question.get_type_object()
        question_json = {
            "id": question.id,
            "questions": {},
            "type": question.question_type,
            "readable_type": question.get_human_readable_type(),
            "choices": [],
        }
        for lang_code, _ in lang_list:
            question_attr = f"question_{lang_code}"
            question_json["questions"][lang_code] = getattr(question, question_attr) or ""
        if question.question_type == "MULTIPLE_CHOICE_FEEDBACK":
            choices = question.get_choices()
            for choice in choices:
                choice_json = {}
                for lang_code, _ in lang_list:
                    answer_attr = f"answer_{lang_code}"
                    choice_json[lang_code] = getattr(choice, answer_attr) or ""
                question_json["choices"].append(choice_json)
        result.append(question_json)

    return JsonResponse({"result": result})


def edit_choices(q_obj, choice_val_dict, lang_list):
    existing_choices = q_obj.get_choices()
    existing_choice_count = len(existing_choices)

    for i, (__, choice_values) in enumerate(sorted(choice_val_dict.items())):
        if existing_choice_count <= i:
            # New choices
            choice_obj = MultipleChoiceFeedbackAnswer(question=q_obj)
            for lang_code, _ in lang_list:
                if lang_code in choice_values:
                    answer = choice_values[lang_code]
                    setattr(choice_obj, f"answer_{lang_code}", answer)
                    choice_obj.save()
        else:
            # Existing choices
            choice_obj = existing_choices[i]
            for lang_code, _ in lang_list:
                if lang_code in choice_values:
                    answer = choice_values[lang_code]
                else:
                    continue
                if getattr(choice_obj, f"answer_{lang_code}") != answer:
                    setattr(choice_obj, f"answer_{lang_code}", answer)
                    choice_obj.save()

    for i, choice_obj in enumerate(existing_choices):
        if i >= len(choice_val_dict):
            choice_obj.delete()


def edit_feedback_questions(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not (request.user.is_staff and request.user.is_authenticated and request.user.is_active):
        return JsonResponse(
            {
                "error": {
                    "__all__": {
                        "message": "Only logged in users can edit feedback questions!",
                        "code": "authentication",
                    }
                }
            }
        )

    data = request.POST.dict()
    data.pop("csrfmiddlewaretoken")

    feedback_questions = ContentFeedbackQuestion.objects.all()
    new_question_str = data.pop("new_questions")
    if new_question_str:
        new_question_ids = new_question_str.split(",")
    else:
        new_question_ids = []

    form = CreateFeedbackQuestionsForm(feedback_questions, new_question_ids, data)

    if form.is_valid():
        cleaned_data = form.cleaned_data
        lang_list = get_lang_list()
        default_lang = get_default_lang()

        # Edit existing feedback questions if necessary
        for q_obj in feedback_questions:
            q_obj = q_obj.get_type_object()
            choice_val_dict = {}
            for lang_code, _ in lang_list:
                question = cleaned_data[f"feedback_question_[{q_obj.id}]_{lang_code}"]
                choice_prefix = f"feedback_choice_[{q_obj.id}]_{lang_code}"
                for field, val in cleaned_data.items():
                    if field.startswith(choice_prefix) and val:
                        choice_id = field[field.index("(") + 1 : field.index(")")]
                        if choice_id in choice_val_dict:
                            choice_val_dict[choice_id][lang_code] = val
                        else:
                            choice_val_dict[choice_id] = {lang_code: val}

                if q_obj.question != question:
                    setattr(q_obj, f"question_{lang_code}", question)
                    q_obj.save()

            if q_obj.question_type == "MULTIPLE_CHOICE_FEEDBACK":
                edit_choices(q_obj, choice_val_dict, lang_list)

        # Add new feedback questions
        new_feedbacks = [
            field
            for field in cleaned_data
            if field.startswith("feedback_question_[new") and default_lang in field
        ]
        for question_field in new_feedbacks:
            question_id = question_field[question_field.index("[") + 1 : question_field.index("]")]
            choices = {}
            question_type = cleaned_data[f"feedback_type_[{question_id}]"]

            if question_type == "THUMB_FEEDBACK":
                q_obj = ThumbFeedbackQuestion()
            elif question_type == "STAR_FEEDBACK":
                q_obj = StarFeedbackQuestion()
            elif question_type == "MULTIPLE_CHOICE_FEEDBACK":
                q_obj = MultipleChoiceFeedbackQuestion()
                choice_fields = [
                    field
                    for field in cleaned_data
                    if field.startswith("feedback_choice_[new") and default_lang in field
                ]
                for choice_field in choice_fields:
                    choice_id = choice_field[choice_field.index("(") + 1 : choice_field.index(")")]
                    choices[choice_id] = MultipleChoiceFeedbackAnswer()
            elif question_type == "TEXTFIELD_FEEDBACK":
                q_obj = TextfieldFeedbackQuestion(question=question)
            else:
                continue

            for lang_code, _ in lang_list:
                question = cleaned_data[f"feedback_question_[{question_id}]_{lang_code}"]
                setattr(q_obj, f"question_{lang_code}", question)
                for choice_id, choice_obj in choices.items():
                    choice_field = f"feedback_choice_[{question_id}]_{lang_code}_({choice_id})"
                    if choice_field in cleaned_data:
                        answer = cleaned_data[choice_field]
                        setattr(choice_obj, f"answer_{lang_code}", answer)
            q_obj.save()
            for choice_obj in choices.values():
                choice_obj.question = q_obj
                choice_obj.save()

    else:
        logger.debug(repr(form.errors))
        return JsonResponse({"error": form.errors})

    return get_feedback_questions(request)


def get_instance_files(request):
    if not (request.user.is_staff and request.user.is_authenticated and request.user.is_active):
        return JsonResponse({"error": "Only logged in admins can query instance files!"})

    if request.user.is_superuser:
        instance_files = InstanceIncludeFile.objects.all()
    else:
        instance_files = InstanceIncludeFile.objects.filter(course__staff_group__user=request.user)

    lang_list = get_lang_list()
    result = []

    for instance_file in instance_files:
        instance_file_json = {
            "id": instance_file.id,
            "instance_id": instance_file.course.id,
            "instance_names": {},
            "default_names": {},
            "descriptions": {},
            "urls": {},
        }

        for lang_code, _ in lang_list:
            default_name_attr = f"default_name_{lang_code}"
            description_attr = f"description_{lang_code}"
            fileinfo_attr = f"fileinfo_{lang_code}"
            name_attr = f"name_{lang_code}"
            try:
                url = getattr(instance_file, fileinfo_attr).url
            except ValueError:
                url = ""
            instance_file_json["urls"][lang_code] = url
            instance_file_json["instance_names"][lang_code] = (
                getattr(instance_file.course, name_attr) or ""
            )
            instance_file_json["default_names"][lang_code] = (
                getattr(instance_file, default_name_attr) or ""
            )
            instance_file_json["descriptions"][lang_code] = (
                getattr(instance_file, description_attr) or ""
            )
        result.append(instance_file_json)

    default_lang = get_default_lang()
    return JsonResponse({"result": sorted(result, key=lambda f: f["default_names"][default_lang])})


def edit_instance_files(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not (request.user.is_staff and request.user.is_authenticated and request.user.is_active):
        return JsonResponse(
            {
                "error": {
                    "__all__": {
                        "message": "Only logged in users can edit instance files!",
                        "code": "authentication",
                    }
                }
            }
        )

    data = request.POST.dict()
    data.pop("csrfmiddlewaretoken")
    files = request.FILES.dict()

    new_file_id_str = data.pop("new_instance_files")
    if new_file_id_str:
        new_file_ids = new_file_id_str.split(",")
    else:
        new_file_ids = []

    if request.user.is_superuser:
        instance_files = InstanceIncludeFile.objects.all()
    else:
        instance_files = InstanceIncludeFile.objects.filter(course__staff_group__user=request.user)
    form = CreateInstanceIncludeFilesForm(instance_files, new_file_ids, data, files)

    if form.is_valid():
        cleaned_data = form.cleaned_data
        lang_list = get_lang_list()
        default_lang = get_default_lang()

        # Edit existing instance files
        for instance_file in instance_files:
            file_changed = False
            with reversion.create_revision():
                for lang_code, _ in lang_list:
                    fileinfo = cleaned_data.get(
                        f"instance_file_file_[{instance_file.id}]_{lang_code}"
                    )
                    default_name = cleaned_data.get(
                        f"instance_file_default_name_[{instance_file.id}]_{lang_code}"
                    )
                    description = cleaned_data.get(
                        f"instance_file_description_[{instance_file.id}]_{lang_code}"
                    )

                    if getattr(instance_file, f"default_name_{lang_code}") != default_name:
                        setattr(instance_file, f"default_name_{lang_code}", default_name)
                        file_changed = True
                    if fileinfo is not None:
                        setattr(instance_file, f"fileinfo_{lang_code}", fileinfo)
                        file_changed = True
                    if (
                        description is not None
                        and getattr(instance_file, f"description_{lang_code}") != description
                    ):
                        setattr(instance_file, f"description_{lang_code}", description)
                        file_changed = True

                course_id = cleaned_data.get(
                    f"instance_file_instance_[{instance_file.id}]_{default_lang}"
                )
                if str(instance_file.course.id) != course_id:
                    instance_file.course_id = course_id
                    file_changed = True

                if file_changed:
                    instance_file.save()

        new_instance_files = {}

        # Create new instance files
        for file_id in new_file_ids:
            with reversion.create_revision():
                instance_file = InstanceIncludeFile()
                for lang_code, _ in lang_list:
                    fileinfo_field = f"instance_file_file_[{file_id}]_{lang_code}"
                    default_name_field = f"instance_file_default_name_[{file_id}]_{lang_code}"
                    description_field = f"instance_file_description_[{file_id}]_{lang_code}"
                    setattr(
                        instance_file,
                        f"fileinfo_{lang_code}",
                        cleaned_data.get(fileinfo_field),
                    )
                    setattr(
                        instance_file,
                        f"default_name_{lang_code}",
                        cleaned_data.get(default_name_field),
                    )
                    setattr(
                        instance_file,
                        f"description_{lang_code}",
                        cleaned_data.get(description_field),
                    )
                instance_field = f"instance_file_instance_[{file_id}]_{default_lang}"
                instance_file.course_id = cleaned_data.get(instance_field)
                instance_file.save()
                new_instance_files[file_id] = instance_file.id

                reversion.set_user(request.user)
    else:
        return JsonResponse({"error": form.errors})

    return get_instance_files(request)


# DOWNLOAD VIEWS
# - currently we need a different view for each file type...


def download_exercise_file(request, exercise_id, file_id, lang_code):
    content = ContentPage.objects.get(id=exercise_id)

    if not determine_access(request.user, content):
        return HttpResponseForbidden(
            _("Only course staff members are allowed to download exercise files.")
        )

    try:
        fileobject = FileExerciseTestIncludeFile.objects.get(id=file_id, exercise__id=exercise_id)
    except FileExerciseTestIncludeFile.DoesNotExist as e:
        return HttpResponseNotFound(_("Requested file does not exist."))

    try:
        fs_path = os.path.join(
            getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT),
            getattr(fileobject, f"fileinfo_{lang_code}").name,
        )
    except AttributeError:
        return HttpResponseNotFound(_("Requested file does not exist."))

    return generate_download_response(fs_path)


def download_instance_file(request, file_id, lang_code):
    try:
        fileobject = InstanceIncludeFile.objects.get(id=file_id)
    except InstanceIncludeFile.DoesNotExist as e:
        return HttpResponseNotFound(_("Requested file does not exist."))

    if not request.user in fileobject.course.staff_group.user_set.get_queryset():
        return HttpResponseForbidden(
            _("Only course staff members are allowed to download instance files.")
        )

    fs_path = os.path.join(
        getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT), fileobject.fileinfo.name
    )

    return generate_download_response(fs_path)
