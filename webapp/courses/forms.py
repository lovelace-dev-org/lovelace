from django.core.exceptions import ValidationError
from django import forms
from django.forms import fields

class TextfieldExerciseForm(forms.Form):
    pass

# http://jacobian.org/writing/dynamic-form-generation/
class MultipleChoiceExerciseForm(forms.Form):
    pass

class CheckboxExerciseForm(forms.Form):
    pass

class FileUploadExerciseForm(forms.Form):
    pass

class CodeInputExerciseForm(forms.Form):
    pass

class CodeReplaceExerciseForm(forms.Form):
    pass
  

class FileEditForm(forms.ModelForm):
    
    def get_initial_for_field(self, field, field_name):
        
        default_value = super().get_initial_for_field(field, field_name)
        
        if isinstance(field, fields.FileField):
            default_value.media_slug = self.initial.get("name")
            default_value.instance_id = self.initial.get("courseinstance")
            default_value.field_name = field_name
        
        return default_value
        
        
class RepeatedTemplateExerciseBackendForm(forms.ModelForm):
    
    def get_initial_for_field(self, field, field_name):
        
        default_value = super().get_initial_for_field(field, field_name)
        
        if isinstance(field, fields.FileField) and default_value:
            default_value.exercise_id = self.initial.get("exercise")
            default_value.filename = self.initial.get("filename")

        return default_value
