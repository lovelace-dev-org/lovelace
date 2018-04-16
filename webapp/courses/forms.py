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
        
        if isinstance(field, fields.FileField) and default_value:
            default_value.media_slug = self.initial.get("name")
            default_value.field_name = field_name
        
        return default_value
        
        
class RepeatedTemplateExerciseBackendForm(forms.ModelForm):
    
    def get_initial_for_field(self, field, field_name):
        
        default_value = super().get_initial_for_field(field, field_name)
        
        if isinstance(field, fields.FileField) and default_value:
            default_value.exercise_id = self.initial.get("exercise")
            default_value.filename = self.initial.get("filename")

        return default_value

class ContentForm(forms.ModelForm):
    
    def _validate_links(self, value):
        import courses.blockparser as blockparser
        import courses.markupparser as markupparser
        from courses.models import ContentPage, CourseMedia, Term
        
        missing_pages = []
        missing_media = []
        missing_terms = []
        messages = []
        
        page_links, media_links = markupparser.LinkParser.parse(value)
        for link in page_links:
            if not ContentPage.objects.filter(slug=link):
                missing_pages.append(link)
                messages.append("Content matching {} does not exist".format(link))
                
        for link in media_links:
            if not CourseMedia.objects.filter(name=link):
                missing_media.append(link)
                messages.append("Media matching {} does not exist".format(link))
                
        term_re = blockparser.tags["term"].re
        
        term_links = set([match.group("term_name") for match in term_re.finditer(value)])
        
        for link in term_links:
            if not Term.objects.filter(name=link):
                missing_terms.append(link)
                messages.append("Term matching {} does not exist".format(link))
                                
        if messages:
            raise ValidationError(messages)
    
    def clean_content_fi(self):
        
        data = self.cleaned_data["content_fi"]
        self._validate_links(data)
        return data
        
    def clean_content_en(self):
        
        data = self.cleaned_data["content_en"]
        self._validate_links(data)
        return data
        