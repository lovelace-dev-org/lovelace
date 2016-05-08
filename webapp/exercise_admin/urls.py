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
    url(r'^file-upload/add-feedback-question$', views.add_feedback_question,
        name='add_feedback_question'),


    # TODO: For administration of other exercise types
    # ...
]
