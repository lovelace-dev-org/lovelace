import itertools

from django.contrib.postgres.forms import SimpleArrayField
from django import forms

import feedback.models
import courses.models as cm

from .utils import get_default_lang, get_lang_list


def lang_code_in_field_name(lang_code, field_name):
    return lang_code in field_name.split("_")[-3:]


def validate_chmod(chmod_str):
    """
    Validate a chmod string such as 'rwxrwxrwx' or 'r-xr-xrwx' by comparing
    each character of the string to '-' or 'rwx'[index of char % 3].
    """
    if len(chmod_str) != 9:
        return False

    return False not in (
        False for i in range(9) if chmod_str[i] != "rwx"[i % 3] and chmod_str[i] != "-"
    )


class CreateFeedbackQuestionsForm(forms.Form):
    def __init__(self, feedback_questions, new_question_ids, data, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        default_lang = get_default_lang()
        lang_list = get_lang_list()

        # Possibly edited existing feedback questions
        for question in feedback_questions:
            self._add_fields(str(question.id), data, default_lang, lang_list)

        # New feedback questions
        for question_id in new_question_ids:
            self._add_fields(question_id, data, default_lang, lang_list)

    def _clean_duplicates_of_field(
        self, field_name, field_val, field_prefix, model_field, cleaned_data, lang_list
    ):
        model_field_readable = model_field.replace("_", " ")

        for lang_code, __ in lang_list:
            if lang_code_in_field_name(lang_code, field_name):
                break

        for k, v in cleaned_data.copy().items():
            if (
                k.startswith(field_prefix)
                and lang_code_in_field_name(lang_code, k)
                and v == field_val
                and k != field_name
            ):
                error_msg = f"Duplicate {model_field_readable} in language {lang_code}!"
                error_code = f"duplicate_{model_field}"
                field_error = forms.ValidationError(error_msg, code=error_code)
                self.add_error(field_name, field_error)

    def _add_fields(self, question_id, data, default_lang, lang_list):
        for lang_code, _ in lang_list:
            question_field = f"feedback_question_[{question_id}]_{lang_code}"

            if lang_code == default_lang:
                self.fields[question_field] = forms.CharField(
                    max_length=100, required=True, strip=True
                )
            else:
                self.fields[question_field] = forms.CharField(
                    max_length=100, required=False, strip=True
                )

            choice_field_prefix = f"feedback_choice_[{question_id}]_{lang_code}"
            choice_fields = sorted([k for k in data.keys() if k.startswith(choice_field_prefix)])
            for i, choice_field in enumerate(choice_fields):
                if i < 2 and lang_code == default_lang:
                    self.fields[choice_field] = forms.CharField(required=True, strip=True)
                else:
                    self.fields[choice_field] = forms.CharField(required=False, strip=True)

        type_field = f"feedback_type_[{question_id}]"
        self.fields[type_field] = forms.ChoiceField(
            choices=feedback.models.QUESTION_TYPE_CHOICES, required=True
        )

    def clean(self):
        cleaned_data = super().clean()
        lang_list = get_lang_list()

        for field_name in self.fields.keys():
            field_val = cleaned_data.get(field_name)
            if field_val is None:
                continue
            question_id = field_name[field_name.index("[") + 1 : field_name.index("]")]

            if field_name.startswith("feedback_question") and field_val:
                self._clean_duplicates_of_field(
                    field_name, field_val, "feedback_question", "question", cleaned_data, lang_list
                )
            elif field_name.startswith("feedback_choice") and field_val:
                self._clean_duplicates_of_field(
                    field_name,
                    field_val,
                    f"feedback_choice_[{question_id}]",
                    "choice",
                    cleaned_data,
                    lang_list,
                )

            if field_name.startswith("choice_field"):
                type_field_name = f"type_field_[{question_id}]"
                if (
                    type_field_name in cleaned_data
                    and cleaned_data[type_field_name] != "MULTIPLE_CHOICE_FEEDBACK"
                ):
                    type_error = forms.ValidationError(
                        "Only multiple choice feedback accepts choice!",
                        code="choices_with_incorrect_type",
                    )
                    self.add_error(type_field_name, type_error)


class CreateInstanceIncludeFilesForm(forms.Form):
    def __init__(self, instance_files, new_file_ids, data, files, *args, **kwargs):
        super().__init__(data, files, *args, **kwargs)

        default_lang = get_default_lang()
        lang_list = get_lang_list()

        # Possibly edited existing instance files
        for instance_file in instance_files:
            self._add_file_fields(str(instance_file.id), default_lang, lang_list)

        for file_id in new_file_ids:
            self._add_file_fields(file_id, default_lang, lang_list)

    def _add_file_fields(self, file_id, default_lang, lang_list):
        for lang_code, _ in lang_list:
            file_field = f"instance_file_file_[{file_id}]_{lang_code}"
            default_name_field = f"instance_file_default_name_[{file_id}]_{lang_code}"
            description_field = f"instance_file_description_[{file_id}]_{lang_code}"

            if lang_code == default_lang and file_id.startswith("new"):
                self.fields[file_field] = forms.FileField(max_length=255, required=True)
            else:
                self.fields[file_field] = forms.FileField(max_length=255, required=False)

            if lang_code == default_lang:
                course_field = f"instance_file_instance_[{file_id}]_{lang_code}"
                course_choices = [
                    (course.id, getattr(course, f"name_{default_lang}"))
                    for course in cm.Course.objects.all()
                ]
                self.fields[default_name_field] = forms.CharField(
                    max_length=255, required=True, strip=True
                )
                self.fields[course_field] = forms.ChoiceField(choices=course_choices, required=True)
            else:
                self.fields[default_name_field] = forms.CharField(
                    max_length=255, required=False, strip=True
                )

            self.fields[description_field] = forms.CharField(required=False, strip=True)

    def _clean_duplicates_of_field(
        self, field_name, field_val, field_prefix, model_field, cleaned_data, lang_list
    ):
        model_field_readable = model_field.replace("_", " ")

        for lang_code, _ in lang_list:
            if lang_code_in_field_name(lang_code, field_name):
                break

        for k, v in cleaned_data.copy().items():
            if (
                k.startswith(field_prefix)
                and lang_code_in_field_name(lang_code, k)
                and v == field_val
                and k != field_name
            ):
                error_msg = f"Duplicate {model_field_readable} in language {lang_code}!"
                error_code = f"duplicate_{model_field}"
                field_error = forms.ValidationError(error_msg, code=error_code)
                self.add_error(field_name, field_error)

    def clean(self):
        cleaned_data = super().clean()
        lang_list = get_lang_list()

        for field_name in self.fields.keys():
            field_val = cleaned_data.get(field_name)
            if field_val is None:
                continue

            if field_name.startswith("instance_file_default_name") and field_val:
                self._clean_duplicates_of_field(
                    field_name,
                    field_val,
                    "instance_file_default_name",
                    "default_name",
                    cleaned_data,
                    lang_list,
                )

            if field_name.startswith("instance_file_chmod") and not validate_chmod(field_val):
                error_msg = "File access mode was of incorrect format! Give 9 character, each either r, w, x or -!"
                error_code = "invalid_chmod"
                field_error = forms.ValidationError(error_msg, code=error_code)
                self.add_error(field_name, field_error)


# Only have required fields for the default language, i.e. LANGUAGE_CODE in
# django.conf.settings.

# The translations for other languages (in django.conf.settings['LANGUAGES'])
# are optional.


def get_sanitized_choices(data, field_name):
    """An ugly hack to deal with a <select multiple> element with dynamic entries."""
    choices = data.getlist(field_name)
    erroneous = set()
    for choice in choices:
        try:
            f_type, f_id = choice.split("_")
            f_id = int(f_id)
        except ValueError as e:
            if f_id[0:3] == "new" and f_id[3:].isdigit():
                pass  # It was a new one
            else:
                erroneous.add(choice)
        else:
            if f_type == "ef":
                # Check if an exercise file with this id exists
                # - Use current form data
                # Check that it's linked to the exercise
                # - Use current form data
                pass
            elif f_type == "if":
                # Check if an exercise file with this id exists
                # - Use current form data
                # Check that it's linked to the exercise
                # - Use current form data
                pass
            else:
                erroneous.add(choice)

    if len(erroneous) > 0:
        return []  # HACK
    return itertools.zip_longest(choices, [], fillvalue="")


class CreateFileUploadExerciseForm(forms.Form):
    # exercise_name = forms.CharField(max_length=255, required=True, strip=True) # Translate
    # exercise_content = forms.CharField(required=False) # Translate
    exercise_default_points = forms.IntegerField(required=True)
    exercise_evaluation_group = forms.CharField(required=False)
    # tags handled at __init__
    exercise_feedback_questions = SimpleArrayField(forms.IntegerField(), required=False)
    # exercise_question = forms.CharField(required=False) # Translate
    exercise_manually_evaluated = forms.BooleanField(required=False)
    exercise_group_submission = forms.BooleanField(required=False)
    exercise_ask_collaborators = forms.BooleanField(required=False)
    exercise_allowed_filenames = forms.CharField(required=False)
    exercise_max_file_count = forms.IntegerField(required=False)
    exercise_answer_mode = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        choices=cm.FileExerciseSettings.ANSWER_MODE_CHOICES
    )

    version_comment = forms.CharField(required=False, strip=True)

    def __init__(
        self, tag_fields, hint_ids, ef_ids, if_ids, order_hierarchy, data, files, *args, **kwargs
    ):
        super().__init__(data, files, *args, **kwargs)

        # Translated fields
        default_lang = get_default_lang()
        lang_list = get_lang_list()
        for lang_code, _ in lang_list:
            # For required fields
            if lang_code == default_lang:
                self.fields[f"exercise_name_{lang_code}"] = forms.CharField(
                    max_length=255, required=True, strip=True
                )
            else:
                self.fields[f"exercise_name_{lang_code}"] = forms.CharField(
                    max_length=255, required=False, strip=True
                )

            # For other fields
            self.fields[f"exercise_content_{lang_code}"] = forms.CharField(required=False)
            self.fields[f"exercise_question_{lang_code}"] = forms.CharField(required=False)
            self.fields[f"exercise_answer_filename_{lang_code}"] = forms.CharField(required=False)

        # Other dynamic fields

        for tag_field in tag_fields:
            self.fields[tag_field] = forms.CharField(min_length=1, max_length=28, strip=True)

        # Hints

        for hint_id in hint_ids:
            for lang_code, _ in lang_list:
                if lang_code == default_lang:
                    self.fields[f"hint_content_[{hint_id}]_{lang_code}"] = forms.CharField(
                        required=True, strip=True
                    )
                else:
                    self.fields[f"hint_content_[{hint_id}]_{lang_code}"] = forms.CharField(
                        required=False, strip=True
                    )

            self.fields[f"hint_tries_[{hint_id}]"] = forms.IntegerField(min_value=0, required=True)

        # Exercise included files

        ef_template = "included_file_{}_[{}]"

        for ef_id in ef_ids:
            for lang_code, _ in lang_list:
                if lang_code == default_lang:
                    self.fields[
                        ef_template.format("default_name", ef_id) + f"_{lang_code}"
                    ] = forms.CharField(required=True)
                    self.fields[
                        ef_template.format("description", ef_id) + f"_{lang_code}"
                    ] = forms.CharField(required=False)
                    self.fields[
                        ef_template.format("name", ef_id) + f"_{lang_code}"
                    ] = forms.CharField(required=True)
                    self.fields[f"included_file_[{ef_id}]_{lang_code}"] = forms.FileField(
                        required=ef_id.startswith("new")
                    )
                else:
                    self.fields[
                        ef_template.format("default_name", ef_id) + f"_{lang_code}"
                    ] = forms.CharField(required=False)
                    self.fields[
                        ef_template.format("description", ef_id) + f"_{lang_code}"
                    ] = forms.CharField(required=False)
                    self.fields[
                        ef_template.format("name", ef_id) + f"_{lang_code}"
                    ] = forms.CharField(required=False)
                    self.fields[f"included_file_[{ef_id}]_{lang_code}"] = forms.FileField(
                        required=False
                    )

            self.fields[ef_template.format("chgrp", ef_id)] = forms.CharField(required=True)
            self.fields[ef_template.format("chmod", ef_id)] = forms.CharField(required=True)
            self.fields[ef_template.format("chown", ef_id)] = forms.CharField(required=True)
            self.fields[ef_template.format("purpose", ef_id)] = forms.CharField(required=True)

        # Instance file links

        for if_id in if_ids:
            for lang_code, _ in lang_list:
                name_field = f"instance_file_name_[{if_id}]_{lang_code}"
                if lang_code == default_lang:
                    self.fields[name_field] = forms.CharField(
                        max_length=255, required=True, strip=True
                    )
                else:
                    self.fields[name_field] = forms.CharField(
                        max_length=255, required=False, strip=True
                    )

            purpose_field = f"instance_file_purpose_[{if_id}]"
            chown_field = f"instance_file_chown_[{if_id}]"
            chgrp_field = f"instance_file_chgrp_[{if_id}]"
            chmod_field = f"instance_file_chmod_[{if_id}]"
            self.fields[purpose_field] = forms.ChoiceField(
                choices=cm.IncludeFileSettings.FILE_PURPOSE_CHOICES, required=False
            )
            self.fields[chown_field] = forms.ChoiceField(
                choices=cm.IncludeFileSettings.FILE_OWNERSHIP_CHOICES, required=False
            )
            self.fields[chgrp_field] = forms.ChoiceField(
                choices=cm.IncludeFileSettings.FILE_OWNERSHIP_CHOICES, required=False
            )
            self.fields[chmod_field] = forms.CharField(max_length=10, required=False, strip=True)

        # Tests, stages and commands

        test_template = "test_{}_{}"
        test_ids = order_hierarchy["stages_of_tests"].keys()

        for test_id in test_ids:
            test_name_field = test_template.format(test_id, "name")
            test_required_files_field = test_template.format(test_id, "required_files")
            choices = get_sanitized_choices(data, test_required_files_field)
            self.fields[test_name_field] = forms.CharField(min_length=1, max_length=200, strip=True)
            self.fields[test_required_files_field] = forms.MultipleChoiceField(
                choices=choices, required=False
            )

        stage_template = "stage_{}_{}"
        stage_ids, command_ids = (
            order_hierarchy["commands_of_stages"].keys(),
            order_hierarchy["commands_of_stages"].values(),
        )

        for stage_id in stage_ids:
            for lang_code, _ in lang_list:
                stage_name_kwargs = {}
                stage_name_field = stage_template.format(stage_id, f"name_{lang_code}")
                self.fields[stage_name_field] = forms.CharField(
                    min_length=1, max_length=64, strip=True, required=False, **stage_name_kwargs
                )
            stage_depends_on_field = stage_template.format(stage_id, "depends_on")
            self.fields[stage_depends_on_field] = forms.IntegerField(required=False)

        command_template = "command_{}_{}"
        command_ids = itertools.chain.from_iterable(command_ids)

        for command_id in command_ids:
            for lang_code, _ in lang_list:
                command_line_kwargs = {}
                command_command_line_field = command_template.format(
                    command_id, f"command_line_{lang_code}"
                )
                if lang_code == default_lang:
                    self.fields[command_command_line_field] = forms.CharField(
                        min_length=1, max_length=255, strip=True, required=True
                    )
                else:
                    self.fields[command_command_line_field] = forms.CharField(
                        min_length=1, max_length=255, strip=True, required=False
                    )
                    command_line_kwargs["required"] = False

                command_input_text_field = command_template.format(
                    command_id, f"input_text_{lang_code}"
                )
                self.fields[command_input_text_field] = forms.CharField(required=False, strip=False)

            command_significant_stdout_field = command_template.format(
                command_id, "significant_stdout"
            )
            command_significant_stderr_field = command_template.format(
                command_id, "significant_stderr"
            )
            command_json_output_field = command_template.format(command_id, "json_output")
            command_return_value_field = command_template.format(command_id, "return_value")
            command_timeout_field = command_template.format(command_id, "timeout")
            self.fields[command_significant_stdout_field] = forms.BooleanField(required=False)
            self.fields[command_significant_stderr_field] = forms.BooleanField(required=False)
            self.fields[command_json_output_field] = forms.BooleanField(required=False)
            self.fields[command_return_value_field] = forms.IntegerField(required=False)
            self.fields[command_timeout_field] = forms.DurationField()

    def _clean_duplicates_of_field(
        self, field_name, field_val, field_prefix, model_field, cleaned_data, lang_list
    ):
        model_field_readable = model_field.replace("_", " ")

        for lang_code, _ in lang_list:
            if lang_code_in_field_name(lang_code, field_name):
                break

        for k, v in cleaned_data.copy().items():
            if (
                k.startswith(field_prefix)
                and lang_code_in_field_name(lang_code, k)
                and v == field_val
                and k != field_name
            ):
                error_msg = f"Duplicate {model_field_readable} in language {lang_code}!"
                error_code = f"duplicate_{model_field}"
                field_error = forms.ValidationError(error_msg, code=error_code)
                self.add_error(field_name, field_error)

    def _validate_links(self, value, lang):
        """
        Goes through the given content field and checks that every embedded
        link to other pages, media files and terms matches an existing one.
        If links to missing entities are found, these are reported as a
        validation error.
        """

        from courses import blockparser
        from courses import markupparser
        from courses.models import ContentPage, CourseMedia, Term

        missing_pages = []
        missing_media = []
        missing_terms = []
        messages = []

        parser = markupparser.LinkParser()
        page_links, media_links = parser.parse(value)
        for link in page_links:
            if not ContentPage.objects.filter(slug=link):
                missing_pages.append(link)
                messages.append(f"Content matching {link} does not exist")

        for link in media_links:
            if not CourseMedia.objects.filter(name=link):
                missing_media.append(link)
                messages.append(f"Media matching {link} does not exist")

        term_re = blockparser.tags["term"].re

        term_links = {match.group("term_name") for match in term_re.finditer(value)}

        for link in term_links:
            if not Term.objects.filter(**{"name_" + lang: link}):
                missing_terms.append(link)
                messages.append(f"Term matching {link} does not exist")

        if messages:
            field_error = forms.ValidationError(messages)
            self.add_error(f"exercise_content_{lang}", field_error)

    def clean(self):
        cleaned_data = super().clean()
        lang_list = get_lang_list()

        for field_name in self.fields.keys():
            field_val = cleaned_data.get(field_name)
            if field_val is None:
                continue

            if field_name.startswith("instance_file_name") and field_val:
                self._clean_duplicates_of_field(
                    field_name, field_val, "instance_file_name", "name", cleaned_data, lang_list
                )

            if field_name.startswith("instance_file_chmod") and not validate_chmod(field_val):
                error_msg = (
                    "File access mode was of incorrect format! "
                    "Give 9 character, each either r, w, x or -!"
                )
                error_code = "invalid_chmod"
                field_error = forms.ValidationError(error_msg, code=error_code)
                self.add_error(field_name, field_error)

            if field_name.startswith("exercise_content_"):
                self._validate_links(field_val, field_name[-2:])

            if field_name.startswith("exercise_allowed_filenames"):
                if field_val:
                    cleaned_data[field_name] = [val.strip() for val in field_val.split(",")]
                else:
                    cleaned_data[field_name] = []

        return cleaned_data
