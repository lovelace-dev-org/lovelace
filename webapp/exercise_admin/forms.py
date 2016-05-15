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
    
        if len(choice_fields) > 99:
            choice_error = forms.ValidationError("Maximum choice count exceeded!", code="max_choices_exceeded")
            self.add_error("choice_field_{}".format(len(choice_fields)), choice_error)
