from django import forms

class AdminFileWidget(forms.ClearableFileInput):
    template_name = 'courses/widgets/modified_file_input.html'
    

class AdminTemplateBackendFileWidget(forms.ClearableFileInput):
    template_name = 'courses/widgets/template_backend_input.html'

class ContentPreviewWidget(forms.Textarea):
    template_name = 'courses/widgets/content_preview_widget.html'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget as an HTML string."""
        context = self.get_context(name, value, attrs)
        return self._render(self.template_name, context, renderer)
