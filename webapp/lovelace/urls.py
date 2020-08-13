from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView
from django.urls.converters import StringConverter

from django.urls import register_converter

from model_path_converter import register_model_converter
from courses.models import Course, CourseInstance, ContentPage, File, User, UserAnswer
from feedback.models import ContentFeedbackQuestion
from utils.converters import Utf8SlugConverter, RevisionConverter, InstanceConverter

register_model_converter(Course, field="slug", base=Utf8SlugConverter)
register_model_converter(ContentPage, name="content", field="slug", base=Utf8SlugConverter)
register_model_converter(User, field="username", base=StringConverter)
register_model_converter(ContentFeedbackQuestion, name="feedback", field="slug", base=Utf8SlugConverter)
register_model_converter(File, name="file", field="name", base=Utf8SlugConverter)
register_model_converter(UserAnswer, name="answer")
register_converter(RevisionConverter, "revision")
register_converter(InstanceConverter, "instance")

# TODO: Design the url hierarchy from scratch
urlpatterns = [
    url(r'^admin/courses/fileuploadexercise/add', RedirectView.as_view(pattern_name='exercise_admin:file_upload_add')),
    url(r'^admin/courses/fileuploadexercise/(?P<exercise_id>\d+)/change', RedirectView.as_view(pattern_name='exercise_admin:file_upload_change')),
    url(r'^admin/', admin.site.urls),
    url(r'^exercise-admin/', include('exercise_admin.urls', namespace="exercise_admin")),
    url(r'^stats/', include('stats.urls', namespace="stats")),
    url(r'^feedback/', include('feedback.urls', namespace="feedback")),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^teacher/', include('teacher_tools.urls', namespace="teacher")),
    url(r'^routine_exercise/', include('routine_exercise.urls', namespace="routine"))
]

try:
    urlpatterns.append(
        url(r'^shib/', include('shibboleth.urls'))
    )
except ImportError:
    # shibboleth is not installed
    pass
finally:
    urlpatterns.append(
        url(r'^', include('courses.urls', namespace="courses")),
    )

if settings.DEBUG:
    try:
        import debug_toolbar
    except ModuleNotFoundError:
        # Django Debug Toolbar not installed
        pass
    else:
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

