from django.http import HttpResponse
from courses.models import Course, Incarnation, ContentPage, TaskPage, RadiobuttonTaskAnswer, CheckboxTaskAnswer
from django.template import Context, RequestContext, loader
from django.core.urlresolvers import reverse

import content_parser

class NavURL:
    def __init__(self, url, name):
        self.url = url
        self.name = name

def index(request):
    course_list = Course.objects.all()
    navurls = [NavURL(reverse('courses.views.index'), "Training home")] # Courses
    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course_list': course_list,
        'navurls': navurls,
        'title': 'Available trainings',
    })
    return HttpResponse(t.render(c))

def course(request, course_name):
    selected_course = Course.objects.get(name=course_name)
    incarnation_list = Incarnation.objects.filter(course=selected_course.id)
    
    # If there's only one incarnation, select it automatically
    #if len(incarnation_list) == 1:
    #    return incarnation(request, course_name, incarnation_list[0].name)

    navurls = [NavURL(reverse('courses.views.index'), "Training home"),
               NavURL(reverse('courses.views.course', kwargs={"course_name":course_name}), course_name),] # Courses
    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'incarnation_list': incarnation_list,
        'course': selected_course,
        'navurls': navurls,
        'title': '%s' % selected_course.name,
    })
    return HttpResponse(t.render(c))

def incarnation(request, course_name, incarnation_name):
    selected_course = Course.objects.get(name=course_name)
    selected_incarnation = Incarnation.objects.get(course=selected_course.id, name=incarnation_name)
    content_list = ContentPage.objects.filter(incarnation=selected_incarnation.id)
    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Course
               NavURL(reverse('courses.views.course', kwargs={"course_name":course_name}), course_name),
               NavURL(reverse('courses.views.incarnation', kwargs={"course_name":course_name, "incarnation_name":incarnation_name}), incarnation_name),]
    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course': selected_course,
        'incarnation': selected_incarnation,
        'content_list': content_list,
        'navurls': navurls,
        'title': '%s' % selected_course.name,
    })
    return HttpResponse(t.render(c))

def content(request, course_name, incarnation_name, content_name, **kwargs):
    import re
    import codecs
    import os

    selected_course = Course.objects.get(name=course_name)
    selected_incarnation = Incarnation.objects.get(course=selected_course.id, name=incarnation_name)
    content = ContentPage.objects.get(incarnation=selected_incarnation.id, name=content_name)

    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Courses
               NavURL(reverse('courses.views.course', kwargs={"course_name":course_name}), course_name),
               NavURL(reverse('courses.views.incarnation', kwargs={"course_name":course_name, "incarnation_name":incarnation_name}), incarnation_name),
               NavURL(reverse('courses.views.content', kwargs={"course_name":course_name, "incarnation_name":incarnation_name, "content_name":content.name}), content.name)]

    rendered_content = u''
    unparsed_content = re.split(r"\r\n|\r|\n", content.content)
    print unparsed_content

    parser = content_parser.ContentParser(iter(unparsed_content))
    parser.set_fileroot(kwargs["media_root"])
    for line in parser.parse():
        include_file_re = re.match("{{\s+(?P<filename>.+)\s+}}", line)
        if include_file_re:
            if include_file_re.group("filename") == parser.get_current_filename():
                file_contents = codecs.open(os.path.join(kwargs["media_root"], course_name, include_file_re.group("filename")), "r", "utf-8").read()
                line = line.replace(include_file_re.group(0), file_contents)
        rendered_content += line

    tasktype = None
    choices = None
    question = None
    try:
        if content.taskpage.radiobuttontask:
            tasktype = "radio"
            choices = RadiobuttonTaskAnswer.objects.filter(task=content.id)
            question = TaskPage.objects.get(id=content.id).question
    except ContentPage.DoesNotExist as e:
        pass

    try:
        if content.taskpage.checkboxtask:
            tasktype = "checkbox"
            choices = CheckboxTaskAnswer.objects.filter(task=content.id)
            question = TaskPage.objects.get(id=content.id).question
    except ContentPage.DoesNotExist as e:
        pass

    try:
        if content.taskpage.textfieldtask:
            tasktype = "textfield"
            question = TaskPage.objects.get(id=content.id).question
    except ContentPage.DoesNotExist as e:
        pass

    try:
        if content.taskpage.filetask:
            tasktype = "file"
            question = TaskPage.objects.get(id=content.id).question
    except ContentPage.DoesNotExist as e:
        pass

    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course': selected_course,
        'incarnation': selected_incarnation,
        'content': rendered_content,
        'content_name': content.name,
        'navurls': navurls,
        'title': '%s - %s' % (content.name, selected_course.name),
        'tasktype': tasktype,
        'question': question,
        'choices': choices,
    })
    return HttpResponse(t.render(c))

def file_download(request, course_name, filename, **kwargs):
    import os
    import mimetypes
    mimetypes.init()
    try:
        file_path = os.path.join(kwargs["media_root"], course_name, filename)
        fd = open(file_path, "rb")
        mime_type_guess = mimetypes.guess_type(file_path)
        response = HttpResponse(fd, mime_type_guess[0])
        return response
    except IOError:
        return HttpResponseNotFound()


# Create your views here.
