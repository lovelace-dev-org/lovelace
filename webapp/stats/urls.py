from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^single-exercise/(?P<content_slug>[^/]+)/$', views.single_exercise, name='single_exercise'),
    url(r'^course-users/(?P<course_slug>[^/]+)/(?P<content_to_search>[^/]+)/(?P<year>\d{4})\-(?P<month>\d{2})\-(?P<day>\d{2})/$', views.course_users, name='course_users'),
    url(r'^all-exercises/(?P<course_name>[^/]+)/$', views.all_exercises, name='all_exercises'),
    url(r'^user-task/(?P<user_name>[^/]+)/(?P<task_name>.+)/$', views.user_task, name='user_task'),
    url(r'^users-all/$', views.users_all, name='users_all'),
    url(r'^users-course/(?P<course>[^/]+)/$', views.users_course, name='users_course'),
]
