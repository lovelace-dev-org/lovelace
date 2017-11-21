from django import forms

class AdminFileWidget(forms.ClearableFileInput):
    template_name = 'courses/widgets/modified_file_input.html'

class AdminTemplateBackendFileWidget(forms.ClearableFileInput):
    template_name = 'courses/widgets/template_backend_input.html'
