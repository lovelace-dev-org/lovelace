import re
import itertools

from django import forms

import feedback.models

class CreateFeedbackQuestionForm(forms.Form):
    def __init__(self, feedback_questions, data, *args, **kwargs):
        super(CreateFeedbackQuestionForm, self).__init__(data, *args, **kwargs)

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
        choice_count = len([k for k in data.keys() if k.startswith(choice_field_prefix)])
        for i in range(choice_count):
            choice_field_name = "{prefix}{{{n}}}".format(prefix=choice_field_prefix, n=i + 1)
            if i < 2:
                self.fields[choice_field_name] = forms.CharField(required=True)
            else:
                self.fields[choice_field_name] = forms.CharField(required=False)
            
    def clean(self):
        cleaned_data = super(CreateFeedbackQuestionForm, self).clean()

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
                        
class CreateFileUploadExerciseForm(forms.Form):
    exercise_name = forms.CharField(max_length=255, required=True, strip=True)
    exercise_content = forms.CharField(required=False)
    exercise_default_points = forms.IntegerField(required=True)
    # tags handled at __init__
    # feedback questions
    exercise_question = forms.CharField(required=False)
    exercise_manually_evaluated = forms.BooleanField(required=False)
    exercise_ask_collaborators = forms.BooleanField(required=False)
    exercise_allowed_filenames = forms.CharField(required=False)

    def __init__(self, tag_count, order_hierarchy, *args, **kwargs):
        super(CreateFileUploadExerciseForm, self).__init__(*args, **kwargs)

        for i in range(tag_count):
            self.fields["exercise_tag_{}".format(i + 1)] = forms.CharField(min_length=1, max_length=28, strip=True)

        test_template = "test_{}_{}"
        test_ids = order_hierarchy["stages_of_tests"].keys()
        
        for test_id in test_ids:
            test_name_field = test_template.format(test_id, "name")
            self.fields[test_name_field] = forms.CharField(min_length=1, max_length=200, strip=True)

        stage_template = "stage_{}_{}"
        stage_ids, command_ids = order_hierarchy["commands_of_stages"].keys(), order_hierarchy["commands_of_stages"].values()

        for stage_id in stage_ids:
            stage_name_field = stage_template.format(stage_id, "name")
            stage_depends_on_field = stage_template.format(stage_id, "depends_on")
            self.fields[stage_name_field] = forms.CharField(min_length=1, max_length=64, strip=True)
            #self.fields[stage_depends_on_field] = ??? #

        command_template = "command_{}_{}"
        command_ids = itertools.chain.from_iterable(command_ids)

        for command_id in command_ids:
            command_command_line_field = command_template.format(command_id, "command_line")
            command_significant_stdout_field = command_template.format(command_id, "significant_stdout")
            command_significant_stderr_field = command_template.format(command_id, "significant_stderr")
            command_input_text_field = command_template.format(command_id, "input_text")
            command_return_value_field = command_template.format(command_id, "return_value")
            command_timeout_field = command_template.format(command_id, "timeout")
            self.fields[command_command_line_field] = forms.CharField(min_length=1, max_length=255, strip=True)
            self.fields[command_significant_stdout_field] = forms.BooleanField(required=False)
            self.fields[command_significant_stderr_field] = forms.BooleanField(required=False)
            self.fields[command_input_text_field] = forms.CharField(required=False, strip=False)
            self.fields[command_return_value_field] = forms.IntegerField(required=False)
            self.fields[command_timeout_field] = forms.DurationField()
        
        def clean(self):
            cleaned_data = super(CreateFileUploadExerciseForm, self).clean()
            
