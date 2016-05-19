import itertools

from django import forms

import feedback.models

class CreateFeedbackQuestionForm(forms.Form):
    question_field = forms.CharField(max_length=100, required=True)
    type_field = forms.ChoiceField(choices=feedback.models.QUESTION_TYPE_CHOICES, required=True)

    def __init__(self, choice_count, *args, **kwargs):
        super(CreateFeedbackQuestionForm, self).__init__(*args, **kwargs)
        for i in range(choice_count):
            if i <= 1:
                self.fields["choice_field_{}".format(i + 1)] = forms.CharField(required=True)
            else:
                self.fields["choice_field_{}".format(i + 1)] = forms.CharField(required=False)

    def clean(self):
        MAX_CHOICE_COUNT = 99
        cleaned_data = super(CreateFeedbackQuestionForm, self).clean()
        question_field = cleaned_data.get("question_field")
        if question_field is not None:
            try:
                feedback.models.ContentFeedbackQuestion.objects.get(question=question_field)
            except feedback.models.ContentFeedbackQuestion.DoesNotExist:
                pass
            else:
                question_error = forms.ValidationError("This feedback question already exists!", code="duplicate_question")
                self.add_error("question_field", question_error)
                
        type_field = cleaned_data.get("type_field")
        if type_field not in [choice[0] for choice in feedback.models.QUESTION_TYPE_CHOICES]:
            type_error = forms.ValidationError("This feedback question type does not exist!", code="invalid_type")
            self.add_error("type_field", type_error)
        
        choice_fields = [k for k in cleaned_data if k.startswith("choice_field")]
        if type_field != "MULTIPLE_CHOICE_FEEDBACK" and len(choice_fields) > 0:
            type_error = forms.ValidationError("Only multiple choice feedback accepts choice!", code="choices_with_incorrect_type")
            self.add_error("type_field", type_error)

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
            
