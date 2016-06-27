import re
import itertools

from django.contrib.postgres.forms import SimpleArrayField
from django import forms
from .utils import get_default_lang, get_lang_list

import feedback.models
import courses.models as c_models

class CreateFeedbackQuestionsForm(forms.Form):
    def __init__(self, feedback_questions, data, *args, **kwargs):
        super(CreateFeedbackQuestionsForm, self).__init__(data, *args, **kwargs)

        # Possibly edited existing feedback questions
        for question in feedback_questions:
            question = question.get_type_object()
            self._add_fields(question.id, data)
            
        # New added feedback questions
        new_feedback_count = len([k for k in data.keys() if k.startswith("question_field_[new")])
        for i in range(new_feedback_count):
            self._add_fields("new-{}".format(i + 1), data)

    def _add_fields(self, prefix_id, data):
        self.fields["question_field_[{}]".format(prefix_id)] = forms.CharField(max_length=100, required=True, strip=True)
        self.fields["type_field_[{}]".format(prefix_id)] = forms.ChoiceField(choices=feedback.models.QUESTION_TYPE_CHOICES, required=True)
        choice_field_prefix = "choice_field_[{}]_".format(prefix_id)
        choice_fields = sorted([k for k in data.keys() if k.startswith(choice_field_prefix)])
        for i, choice_field in enumerate(choice_fields):
            if i < 2:
                self.fields[choice_field] = forms.CharField(required=True, strip=True)
            else:
                self.fields[choice_field] = forms.CharField(required=False, strip=True)
            
    def clean(self):
        cleaned_data = super(CreateFeedbackQuestionsForm, self).clean()

        for k1 in self.fields.keys():
            field_val = cleaned_data.get(k1)
            if field_val is None:
                continue
            
            if k1.startswith("question_field"):
                for k2, v in cleaned_data.copy().items():
                    if k2.startswith("question_field") and v == field_val and k1 != k2:
                        question_error = forms.ValidationError("Duplicate feedback question!", code="duplicate_question")
                        self.add_error(k1, question_error)
                try:
                    feedback_question = feedback.models.ContentFeedbackQuestion.objects.get(question=field_val)
                except feedback.models.ContentFeedbackQuestion.DoesNotExist:
                    pass
                else:
                    question_id = re.findall("\[(.*?)\]", k1)[0]
                    if str(feedback_question.get_type_object().id) != question_id:
                        #TODO: handle swapping of names
                        question_error = forms.ValidationError("A feedback question with this name already exists! Remove the duplicate first!",
                                                               code="question_exists")
                        self.add_error(k1, question_error)

            elif k1.startswith("type_field"):
                if field_val not in [choice[0] for choice in feedback.models.QUESTION_TYPE_CHOICES]:
                    type_error = forms.ValidationError("This feedback question is of invalid type!", code="invalid_type")
                    self.add_error(k, type_error)

            elif k1.startswith("choice_field"):
                question_id = re.findall("\[(.*?)\]", k1)[0]
                type_field_name = "type_field_[{}]".format(question_id)
                if type_field_name in cleaned_data and cleaned_data[type_field_name] != "MULTIPLE_CHOICE_FEEDBACK":
                    type_error = forms.ValidationError("Only multiple choice feedback accepts choice!", code="choices_with_incorrect_type")
                    self.add_error(type_field_name, type_error)
                for k2, v in cleaned_data.copy().items():
                    if k2.startswith("choice_field_[{}]".format(question_id)) and v == field_val and k1 != k2:
                        choice_error = forms.ValidationError("Duplicate choice!", code="duplicate_choice")
                        self.add_error(k1, choice_error)


class CreateInstanceIncludeFilesForm(forms.Form):
    def __init__(self, instance_files, new_file_ids, linked_file_ids, data, files, *args, **kwargs):
        super(CreateInstanceIncludeFilesForm, self).__init__(data, files, *args, **kwargs)

        default_lang = get_default_lang()
        lang_list = get_lang_list()

        # Possibly edited existing instance files
        for instance_file in instance_files:
            self._add_file_fields(str(instance_file.id), default_lang, lang_list)

        for file_id in new_file_ids:
            self._add_file_fields(file_id, default_lang, lang_list)

        for file_id in linked_file_ids:
            self._add_link_fields(file_id, default_lang, lang_list)

    def _add_file_fields(self, file_id, default_lang, lang_list):
        for lang_code, _ in lang_list:
            file_field = "instance_file_file_[{id}]_{lang}".format(id=file_id, lang=lang_code)
            default_name_field = "instance_file_default_name_[{id}]_{lang}".format(id=file_id, lang=lang_code)
            description_field = "instance_file_description_[{id}]_{lang}".format(id=file_id, lang=lang_code)

            if lang_code == default_lang and file_id.startswith("new"):
                self.fields[file_field] = forms.FileField(max_length=255, required=True)
            else:
                self.fields[file_field] = forms.FileField(max_length=255, required=False)
                
            if lang_code == default_lang:
                self.fields[default_name_field] = forms.CharField(max_length=255, required=True, strip=True)
            else:
                self.fields[default_name_field] = forms.CharField(max_length=255, required=False, strip=True)

            self.fields[description_field] = forms.CharField(required=False, strip=True)

        instance_field = "instance_file_instance_[{}]".format(file_id)
        instance_choices = [(instance.id, instance.name) for instance in c_models.CourseInstance.objects.all()]
        self.fields[instance_field] = forms.ChoiceField(choices=instance_choices, required=True)

    def _add_link_fields(self, file_id, default_lang, lang_list):
        for lang_code, _ in lang_list:
            name_field = "instance_file_name_[{id}]_{lang}".format(id=file_id, lang=lang_code)
            if lang_code == default_lang:
                self.fields[name_field] = forms.CharField(max_length=255, required=True, strip=True)
            else:
                self.fields[name_field] = forms.CharField(max_length=255, required=False, strip=True)

        purpose_field = "instance_file_purpose_[{id}]".format(id=file_id)
        chown_field = "instance_file_chown_[{id}]".format(id=file_id)
        chgrp_field = "instance_file_chgrp_[{id}]".format(id=file_id)
        chmod_field = "instance_file_chmod_[{id}]".format(id=file_id)
        self.fields[purpose_field] = forms.ChoiceField(choices=c_models.IncludeFileSettings.FILE_PURPOSE_CHOICES, required=False)
        self.fields[chown_field] = forms.ChoiceField(choices=c_models.IncludeFileSettings.FILE_OWNERSHIP_CHOICES, required=False)
        self.fields[chgrp_field] = forms.ChoiceField(choices=c_models.IncludeFileSettings.FILE_OWNERSHIP_CHOICES, required=False)
        self.fields[chmod_field] = forms.CharField(max_length=10, required=False, strip=True) 

    def _clean_duplicates_of_field(self, field_name, field_val, model_field, cleaned_data, lang_list):
        field_prefix = "instance_file_{}".format(model_field)
        model_field_readable = model_field.replace("_", " ")
        
        for lang_code, _ in lang_list:
            if field_name.startswith(field_prefix) and field_name.endswith(lang_code) and field_val != "":
                for k, v in cleaned_data.copy().items():
                    if k.startswith(field_prefix) and k.endswith(lang_code) and v == field_val and k != field_name:
                        error_msg = "Duplicate {field} in language {lang}!".format(field=model_field_readable, lang=lang_code)
                        error_code = "duplicate_{}".format(model_field)
                        field_error = forms.ValidationError(error_msg, code=error_code)
                        self.add_error(field_name, field_error)
        
    def clean(self):
        cleaned_data = super(CreateInstanceIncludeFilesForm, self).clean()
        lang_list = get_lang_list()

        for field_name in self.fields.keys():
            field_val = cleaned_data.get(field_name)
            if field_val is None:
                continue

            self._clean_duplicates_of_field(field_name, field_val, "default_name", cleaned_data, lang_list)
            self._clean_duplicates_of_field(field_name, field_val, "name", cleaned_data, lang_list)

            chmod_pattern = "^((r|-)(w|-)(x|-)){3}$"
            if field_name.startswith("instance_file_chmod") and not re.match(chmod_pattern, field_val):
                error_msg = "File access mode was of incorrect format! Give 9 character, each either r, w, x or -!"
                error_code = "invalid_chmod"
                field_error = forms.ValidationError(error_msg, code=error_code)
                self.add_error(field_name, field_error)

# Only have required fields for the default language, i.e. LANGUAGE_CODE in
# django.conf.settings.

# The translations for other languages (in django.conf.settings['LANGUAGES'])
# are optional.

def get_sanitized_choices(data, field_name):
    '''An ugly hack to deal with a <select multiple> element with dynamic entries.
    '''
    choices = data.getlist(field_name)
    erroneous = set()
    for choice in choices:
        try:
            f_type, f_id = choice.split('_')
            f_id = int(f_id)
        except ValueError as e:
            erroneous.add(choice)
        else:
            if f_type == 'ef':
                # Check if an exercise file with this id exists
                # - Use current form data
                # Check that it's linked to the exercise
                # - Use current form data
                pass
            elif f_type == 'if':
                # Check if an exercise file with this id exists
                # - Use current form data
                # Check that it's linked to the exercise
                # - Use current form data
                pass
            else:
                erroneous.add(choice)

    if len(erroneous) > 0:
        return [] # HACK
    return itertools.zip_longest(choices, [], fillvalue='')

class CreateFileUploadExerciseForm(forms.Form):
    #exercise_name = forms.CharField(max_length=255, required=True, strip=True) # Translate
    #exercise_content = forms.CharField(required=False) # Translate
    exercise_default_points = forms.IntegerField(required=True)
    # tags handled at __init__
    exercise_feedback_questions = SimpleArrayField(forms.IntegerField())
    #exercise_question = forms.CharField(required=False) # Translate
    exercise_manually_evaluated = forms.BooleanField(required=False)
    exercise_ask_collaborators = forms.BooleanField(required=False)
    exercise_allowed_filenames = forms.CharField(required=False)
    version_comment = forms.CharField(required=False, strip=True)

    def __init__(self, tag_fields, order_hierarchy, data, *args, **kwargs):
        super(CreateFileUploadExerciseForm, self).__init__(data, *args, **kwargs)

        # Translated fields
        # TODO: How to get these dynamically?
        default_lang = get_default_lang()
        lang_list = get_lang_list()
        for lang_code, _ in lang_list:
            # For required fields
            if lang_code == default_lang:
                self.fields['exercise_name_{}'.format(lang_code)] = forms.CharField(max_length=255, required=True, strip=True)
            else:
                self.fields['exercise_name_{}'.format(lang_code)] = forms.CharField(max_length=255, required=False, strip=True)

            # For other fields
            self.fields['exercise_content_{}'.format(lang_code)] = forms.CharField(required=False)
            self.fields['exercise_question_{}'.format(lang_code)] = forms.CharField(required=False)

        # Other dynamic fields

        for tag_field in tag_fields:
            self.fields[tag_field] = forms.CharField(min_length=1, max_length=28, strip=True)

        test_template = "test_{}_{}"
        test_ids = order_hierarchy["stages_of_tests"].keys()
        
        for test_id in test_ids:
            test_name_field = test_template.format(test_id, "name")
            test_required_files_field = test_template.format(test_id, 'required_files')
            choices = get_sanitized_choices(data, test_required_files_field)
            self.fields[test_name_field] = forms.CharField(min_length=1, max_length=200, strip=True)
            self.fields[test_required_files_field] = forms.MultipleChoiceField(choices=choices, required=False)

        stage_template = "stage_{}_{}"
        stage_ids, command_ids = order_hierarchy["commands_of_stages"].keys(), order_hierarchy["commands_of_stages"].values()

        for stage_id in stage_ids:
            for lang_code, _ in lang_list:
                stage_name_kwargs = {}
                stage_name_field = stage_template.format(stage_id, 'name_{}'.format(lang_code))
                if lang_code != default_lang:
                    stage_name_kwargs['required'] = False
                self.fields[stage_name_field] = forms.CharField(min_length=1, max_length=64, strip=True, **stage_name_kwargs)
            stage_depends_on_field = stage_template.format(stage_id, "depends_on")
            self.fields[stage_depends_on_field] = forms.IntegerField(required=False)

        command_template = "command_{}_{}"
        command_ids = itertools.chain.from_iterable(command_ids)

        for command_id in command_ids:
            for lang_code, _ in lang_list:
                command_line_kwargs = {}
                command_command_line_field = command_template.format(command_id, 'command_line_{}'.format(lang_code))
                if lang_code != default_lang:
                    command_line_kwargs['required'] = False
                self.fields[command_command_line_field] = forms.CharField(min_length=1, max_length=255, strip=True)
            
                command_input_text_field = command_template.format(command_id, 'input_text_{}'.format(lang_code))
                self.fields[command_input_text_field] = forms.CharField(required=False, strip=False)
                
            command_significant_stdout_field = command_template.format(command_id, "significant_stdout")
            command_significant_stderr_field = command_template.format(command_id, "significant_stderr")
            command_return_value_field = command_template.format(command_id, "return_value")
            command_timeout_field = command_template.format(command_id, "timeout")
            self.fields[command_significant_stdout_field] = forms.BooleanField(required=False)
            self.fields[command_significant_stderr_field] = forms.BooleanField(required=False)
            self.fields[command_return_value_field] = forms.IntegerField(required=False)
            self.fields[command_timeout_field] = forms.DurationField()
        
    def clean(self):
        cleaned_data = super(CreateFileUploadExerciseForm, self).clean()

        return cleaned_data
            
