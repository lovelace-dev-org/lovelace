import re
import itertools

from django.contrib.postgres.forms import SimpleArrayField
from django import forms
from .utils import get_default_lang, get_lang_list

import feedback.models

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
        self.fields["question_field_[{}]".format(prefix_id)] = forms.CharField(max_length=100, required=True)
        self.fields["type_field_[{}]".format(prefix_id)] = forms.ChoiceField(choices=feedback.models.QUESTION_TYPE_CHOICES, required=True)
        choice_field_prefix = "choice_field_[{}]_".format(prefix_id)
        choice_fields = sorted([k for k in data.keys() if k.startswith(choice_field_prefix)])
        for i, choice_field in enumerate(choice_fields):
            if i < 2:
                self.fields[choice_field] = forms.CharField(required=True)
            else:
                self.fields[choice_field] = forms.CharField(required=False)
            
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
    def __init__(self, feedback_questions, data, *args, **kwargs):
        super(CreateInstanceIncludeFilesForm, self).__init__(data, *args, **kwargs)

    def clean(self):
        cleaned_data = super(CreateFeedbackQuestionsForm, self).clean()
    
# Only have required fields for the default language, i.e. LANGUAGE_CODE in
# django.conf.settings.

# The translations for other languages (in django.conf.settings['LANGUAGES'])
# are optional.

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

    def __init__(self, tag_fields, order_hierarchy, *args, **kwargs):
        super(CreateFileUploadExerciseForm, self).__init__(*args, **kwargs)

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
            self.fields[test_name_field] = forms.CharField(min_length=1, max_length=200, strip=True)

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
            
