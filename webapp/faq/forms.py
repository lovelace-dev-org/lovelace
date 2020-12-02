from django import forms
from django.utils.translation import ugettext as _
from modeltranslation.forms import TranslationModelForm
from faq.models import FaqQuestion

class FaqQuestionForm(TranslationModelForm):
    
    class Meta:
        model = FaqQuestion
        fields = ["question", "answer", "hook"]
        widgets = {
            "question": forms.Textarea(attrs={"class": "generic-textfield", "rows": 2}),
            "answer": forms.Textarea(attrs={"class": "generic-textfield", "rows": 5}),
        }
        
    action = forms.ChoiceField(
        widget=forms.HiddenInput,
        choices=(("create", "create"), ("edit", "edit")),
        initial="create"
    )
    
        
class FaqLinkForm(forms.Form):

    def __init__(self, *args, **kwargs):
        questions = kwargs.pop("available_questions")
        super().__init__(*args, **kwargs)

        self.fields["question_select"] = forms.ChoiceField(
            widget = forms.Select,
            label = _("Choose question to link"),
            choices = [("", "------------"), ] + [(q.hook, q.question) for q in questions]
        )
        
        
            
            
        
    
    
        

