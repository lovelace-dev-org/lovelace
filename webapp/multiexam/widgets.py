from django import forms


class AdminMultiexamFileWidget(forms.ClearableFileInput):
    template_name = "multiexam/widgets/multiexam_question_pool_widget.html"
