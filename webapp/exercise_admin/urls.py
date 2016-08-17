from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    ## For administration (add/edit) of file upload exercises
    url(r'^file-upload/add$', views.file_upload_exercise, {'action': 'add'},
        name='file_upload_add'),
    url(r'^file-upload/(?P<exercise_id>\d+)/change$', views.file_upload_exercise,
        {'action': 'change'}, name='file_upload_change'),

    # File upload exercise related objects
    url(r'^instance-files$', views.get_instance_files,
        name='get_instance_files'),
    url(r'^instance_files/edit$', views.edit_instance_files,
        name='edit_instance_files'),
    url(r'^feedback-questions$', views.get_feedback_questions,
        name='get_feedback_questions'),
    url(r'^feedback-questions/edit$', views.edit_feedback_questions,
        name='edit_feedback_questions'),

    # TODO: For administration (add/edit) of other exercise types
    # ...
]
