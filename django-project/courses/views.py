from django.http import HttpResponse
from courses.models import Course
from django.template import Context, RequestContext, loader
from django.core.urlresolvers import reverse

def index(request):
    course_list = Course.objects.all()
    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course_list': course_list,
        'courses_url': reverse('courses.views.index')
    })
    return HttpResponse(t.render(c))

def course(request, course_name):
    pass

def incarnation(request, course_name, incarnation_name):
    pass

def content(request, course_name, incarnation_name, content_name):
    pass

# Create your views here.
