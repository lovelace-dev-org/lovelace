from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),

    # For administration of file upload exercises
    url(r'^file-upload/add$', views.file_upload_exercise, {'action': 'add'},
        name='file_upload_add'),
    url(r'^file-upload/(?P<exercise_id>\d+)/change$', views.file_upload_exercise,
        {'action': 'change'}, name='file_upload_change'),
    url(r'^file-upload/(?P<exercise_id>\d+)/delete$', views.file_upload_exercise,
        name='file_upload_delete'),    
    url(r'^instance-files/(?P<exercise_id>\d+)$', views.get_instance_files,
        name='get_instance_files'),
    url(r'^instance_files/(?P<exercise_id>\d+)/edit$', views.edit_instance_files,
        name='edit_instance_files'),
    url(r'^feedback-questions$', views.get_feedback_questions,
        name='get_feedback_questions'),
    url(r'^feedback-questions/edit$', views.edit_feedback_questions,
        name='edit_feedback_questions'),

    # TODO: For administration of other exercise types
    # ...
]
