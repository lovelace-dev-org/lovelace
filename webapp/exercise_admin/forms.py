from django import forms

import feedback.models

class CreateFeedbackQuestionForm(forms.Form):
    question_field = forms.CharField(max_length=100, required=True)
    type_field = forms.ChoiceField(choices=feedback.models.QUESTION_TYPE_CHOICES, required=True)

    def __init__(self, choice_count, *args, **kwargs):
        super(CreateFeedbackQuestionForm, self).__init__(*args, **kwargs)
        for i in range(choice_count):
            self.fields["choice_field_{}".format(i + 1)] = forms.CharField()

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
                raise forms.ValidationError("Feedback question {} already exists!".format(question_field), code="duplicate_question")
                
        type_field = cleaned_data.get("type_field")
        choice_fields = [k for k in cleaned_data if k.startswith("choice_field")]
        if len(choice_fields) > 99:
            raise forms.ValidationError("Maximum choice count exceeded!")
        
        if type_field == "MULTIPLE_CHOICE_FEEDBACK" and len(choice_fields) == 0:
            raise forms.ValidationError("If multiple choice feedback is chosen, at least one choice must be provided!", code="no_choices")
        elif type_field != "MULTIPLE_CHOICE_FEEDBACK" and len(choice_fields) > 0:
            raise forms.ValidationError("Only multiple choice feedback accepts choices!", code="choices_with_invalid_type")
            
