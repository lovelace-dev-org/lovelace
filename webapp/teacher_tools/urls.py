from django.conf.urls import include, url

from . import views

app_name = "teacher_tools"

urlpatterns = [
    
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/(?P<content_slug>[^/]+)/download_answers/$', views.download_answers, name="download_answers"),
    
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/enrollments/$', views.manage_enrollments, name="manage_enrollments"),
    
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/completion/(?P<user>[^/]+)/$', views.student_course_completion, name="student_completion"),
    
    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/completion/$', views.course_completion, name="completion"),

    url(r'^(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/completion-csv/$', views.course_completion_csv, name="completion_csv"),
]

