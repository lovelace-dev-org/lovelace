from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.views.generic import RedirectView
from django.urls.converters import StringConverter

from django.urls import path, register_converter

from model_path_converter import register_model_converter
from courses.models import Course, CourseInstance, ContentPage, File, StudentGroup,\
                           GroupInvitation, User, UserAnswer, Calendar, CalendarDate
from feedback.models import ContentFeedbackQuestion
from utils.converters import Utf8SlugConverter, RevisionConverter, InstanceConverter

register_model_converter(Course, field="slug", base=Utf8SlugConverter)
register_model_converter(ContentPage, name="content", field="slug", base=Utf8SlugConverter)
register_model_converter(User, field="username", base=StringConverter)
register_model_converter(StudentGroup, "group")
register_model_converter(GroupInvitation, "invite")
register_model_converter(ContentFeedbackQuestion, name="feedback", field="slug", base=Utf8SlugConverter)
register_model_converter(File, name="file", field="name", base=Utf8SlugConverter)
register_model_converter(UserAnswer, name="answer")
register_converter(RevisionConverter, "revision")
register_converter(InstanceConverter, "instance")
register_model_converter(Calendar, name="calendar")
register_model_converter(CalendarDate, name="event")

# TODO: Design the url hierarchy from scratch
urlpatterns = [
    path('admin/courses/fileuploadexercise/add', RedirectView.as_view(pattern_name='exercise_admin:file_upload_add')),
    path('admin/courses/fileuploadexercise/<int:exercise_id>>/change', RedirectView.as_view(pattern_name='exercise_admin:file_upload_change')),
    path('admin/', admin.site.urls),
    path('exercise-admin/', include('exercise_admin.urls', namespace="exercise_admin")),
    path('stats/', include('stats.urls', namespace="stats")),
    path('feedback/', include('feedback.urls', namespace="feedback")),
    path('i18n/', include('django.conf.urls.i18n')),
    path('accounts/', include('allauth.urls')),
    path('teacher/', include('teacher_tools.urls', namespace="teacher")),
    path('routine_exercise/', include('routine_exercise.urls', namespace="routine")),
    path('faq/', include('faq.urls', namespace="faq")),
    path('assessment/', include('assessment.urls', namespace="assessment")),
]

try:
    urlpatterns.append(
        path('shib/', include('shibboleth.urls'))
    )
except ImportError:
    # shibboleth is not installed
    pass
finally:
    urlpatterns.append(
        path('', include('courses.urls', namespace="courses")),
    )

if settings.DEBUG:
    try:
        import debug_toolbar
    except ModuleNotFoundError:
        # Django Debug Toolbar not installed
        pass
    else:
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

