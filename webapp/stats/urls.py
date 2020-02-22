from django.urls import path

from . import views

app_name="stats"

urlpatterns = [
    path("single-exercise/<content:exercise>/", views.single_exercise, name="single_exercise"),
    #path("course-users/<course:course>/(?P<content_to_search>[^/]+)/(?P<year>\d{4})\-(?P<month>\d{2})\-(?P<day>\d{2})/#$", views.course_users, name="course_users"),
    #url(r"^all-exercises/(?P<course_name>[^/]+)/$", views.all_exercises, name="all_exercises"),
    #url(r"^user-task/(?P<user_name>[^/]+)/(?P<task_name>.+)/$", views.user_task, name="user_task"),
    #url(r"^users-all/$", views.users_all, name="users_all"),
    #url(r"^users-course/(?P<course_slug>[^/]+)/(?P<instance_slug>[^/]+)/$", views.users_course, name="users_course"),
    
    path("instance-console/<course:course>/<instance:instance>/", views.instance_console, name="instance_console"),
    path("generate/<course:course>/<instance:instance>/", views.generate_instance_stats, name="generate_instance_stats"),
]
