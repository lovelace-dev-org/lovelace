from django import forms

class AdminRoutineBackendFileWidget(forms.ClearableFileInput):
    template_name = 'routine_exercise/widgets/routine_backend_input.html'
