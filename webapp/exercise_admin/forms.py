import re
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
    exercise_content = forms.CharField()
    exercise_default_points = forms.IntegerField(required=True)
    # handle tags as forms.Charfield(min_length=1, max_length=28, strip=True)
    # feedback questions
    exercise_question = forms.CharField()
    exercise_manually_evaluated = forms.BooleanField()
    exercise_ask_collaborators = forms.BooleanField()
    exercise_allowed_filenames = forms.CharField()
    

