"""
Django views.
TODO: Heavy commenting!
"""
from django.http import HttpResponse
from courses.models import Course, Incarnation, ContentPage, TaskPage, RadiobuttonTaskAnswer, CheckboxTaskAnswer, TextfieldTaskAnswer, ContentGraphNode, File
from django.template import Context, RequestContext, loader
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper

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

def traverse_tree(list_tree):
    from django.utils.safestring import mark_safe
    tree = []
    
    if list_tree:
        if isinstance(list_tree, list):
            tree.append(mark_safe('>'))
            for leaf in list_tree:
                result = traverse_tree(leaf)
                tree.extend(result)
            tree.append(mark_safe('<'))
        else:
            tree.append(list_tree)

    return tree

import graph_builder

def course_graph(request, course_name, incarnation_name):
    import codecs
    import os
    selected_course = Course.objects.get(name=course_name)
    selected_incarnation = Incarnation.objects.get(course=selected_course.id, name=incarnation_name)
    course_graph_nodes = ContentGraphNode.objects.filter(incarnation=selected_incarnation.id)

    nodes = []
    edges = []
    root_node = graph_builder.Node({"name":"start","shape":"point","width":"0.1","height":"0.1"})
    nodes.append(root_node)
    for graph_node in course_graph_nodes:
        #node = graph_builder.Node(graph_node)
        content = ContentPage.objects.get(id=graph_node.content_id)
        node_url = reverse('courses.views.content', kwargs={"course_name":course_name, "incarnation_name":incarnation_name, "content_name":content.name})
        label = content.name # TODO: Use a shorter name
        node = graph_builder.Node({"name":"node%d" % (graph_node.id),
                                   "style":"filled",
                                   "fillcolor":"#55aaff",
                                   "href":node_url,
                                   "label":label,
                                   "fontname":"Arial",
                                   "fontsize":"13",
                                   })
        if graph_node.parentnode_id:
            #parent_node = graph_builder.Node(course_graph_nodes.get(id=graph_node.parentnode_id))
            parent_node = graph_builder.Node({"name":"node%d" % (graph_node.parentnode_id),})
        else:
            parent_node = root_node # Parent node id was None
        edge = graph_builder.Edge(parent_node, node)
        edges.append(edge)
        nodes.append(node)

    graph = graph_builder.Graph(nodes, edges)

    # TODO: Use templates and temporary files to achieve this
    uncompiled_graph = codecs.open("uncompiled.vg", "w", "utf-8")
    uncompiled_graph.write("digraph course_graph {\n")
    uncompiled_graph.write('    node [penwidth="2",fixedsize="True",width="1.6",height="0.5"]\n')
    for node in graph.nodes:
        uncompiled_graph.write("    %s\n" % (node))
    for edge in graph.edges:
        uncompiled_graph.write("    %s\n" % (edge))
    uncompiled_graph.write("}\n")
    uncompiled_graph.close()

    os.system("dot uncompiled.vg -Txdot -ograph.vg")

    graph_file = codecs.open("graph.vg", "r", "utf-8")
    #graph_file = codecs.open("uncompiled.vg", "r", "utf-8") # to debug the uncompile dot file

    # http://stackoverflow.com/questions/908258/generating-file-to-download-with-django
    response = HttpResponse(FileWrapper(graph_file), content_type='text/plain')
    #response['Content-Disposition'] = 'attachment; filename=graph.vg'
    return response
 
def incarnation(request, course_name, incarnation_name):
    selected_course = Course.objects.get(name=course_name)
    selected_incarnation = Incarnation.objects.get(course=selected_course.id, name=incarnation_name)
    content_list = ContentPage.objects.filter(incarnation=selected_incarnation.id)
    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Course
               NavURL(reverse('courses.views.course', kwargs={"course_name":course_name}), course_name),
               NavURL(reverse('courses.views.incarnation', kwargs={"course_name":course_name, "incarnation_name":incarnation_name}), incarnation_name),]

    course_graph_url = reverse('courses.views.course_graph', kwargs={'course_name':course_name, 'incarnation_name':incarnation_name})

    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course': selected_course,
        'incarnation': selected_incarnation,
#        'content_list': content_list,
#        'content_tree': tree, #course_tree.getChildren(),
        'course_graph_url': course_graph_url,
        'navurls': navurls,
        'title': '%s' % selected_incarnation.name,
    })
    return HttpResponse(t.render(c))

def get_task_info(content):
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

    return (tasktype, question, choices)


def content(request, course_name, incarnation_name, content_name, **kwargs):
    import re
    import codecs
    import os

    selected_course = Course.objects.get(name=course_name)
    selected_incarnation = Incarnation.objects.get(course=selected_course.id, name=incarnation_name)
    content = ContentPage.objects.get(incarnation=selected_incarnation.id, name=content_name)
    pages = [content]

    # Validate an answer to question
    if request.POST:
        print "here we are"
        question = TaskPage.objects.get(id=content.id).question

        correct = True
        tasktype = None
        choices = None
        answers = None
        hints = []

        try:
            if content.taskpage.radiobuttontask:
                choices = RadiobuttonTaskAnswer.objects.filter(task=content.id)
                tasktype = "radiobutton"
                
        except ContentPage.DoesNotExist as e:
            pass

        if choices and tasktype == "radiobutton":
            for choice in choices:
                if request.POST[str(choice.id)] == "true" and choice.correct == True and correct == True:
                    correct = True
                elif request.POST[str(choice.id)] == "false" and choice.correct == True:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)
                elif request.POST[str(choice.id)] == "true" and choice.correct == False:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)
                    break

        try:
            if content.taskpage.checkboxtask:
                choices = CheckboxTaskAnswer.objects.filter(task=content.id)
                tasktype = "checkbox"
        except ContentPage.DoesNotExist as e:
            pass

        if choices and tasktype == "checkbox":
            for choice in choices:
                if request.POST[str(choice.id)] == "true" and choice.correct == True and correct == True:
                    correct = True
                elif request.POST[str(choice.id)] == "false" and choice.correct == True:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)
                elif request.POST[str(choice.id)] == "true" and choice.correct == False:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)

        try:
            if content.taskpage.textfieldtask:
                answers = TextfieldTaskAnswer.objects.filter(task=content.id)
                tasktype = "textfield"
        except ContentPage.DoesNotExist as e:
            pass

        if answers and tasktype == "textfield":
            given = request.POST["answer"]
            for answer in answers:
                if answer.regexp:
                    import re
                    # TODO: Regexp error checking!!!! To prevent crashes.
                    if re.match(answer.answer, given) and answer.correct and correct == True:
                        correct = True
                        break
                    elif re.match(answer.answer, given) and not answer.correct:
                        correct = False
                        if answer.hint:
                            hints.append(answer.hint)
                    elif not re.match(answer.answer, given):
                        correct = False
                        if answer.hint:
                            hints.append(answer.hint)
                else:
                    if given == answer.answer and answer.correct and correct == True:
                        correct = True
                        break
                    elif given == answer.answer and not answer.correct:
                        correct = False
                        if answer.hint:
                            hints.append(answer.hint)
                    elif given != answer.answer:
                        correct = False
                        if answer.hint:
                            hints.append(answer.hint)

        # TODO: Use a template here to make it look nicer.
        if correct:
            response_string = u"Correct!"
        else:
            response_string = u"Incorrect answer.<br />"
            if hints:
                import random
                random.shuffle(hints)
                response_string += "<br />".join(hints)

        response = HttpResponse(response_string)
        return response

    # back to normal flow (representing a content page)

    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Courses
               NavURL(reverse('courses.views.course', kwargs={"course_name":course_name}), course_name),
               NavURL(reverse('courses.views.incarnation', kwargs={"course_name":course_name, "incarnation_name":incarnation_name}), incarnation_name),
               NavURL(reverse('courses.views.content', kwargs={"course_name":course_name, "incarnation_name":incarnation_name, "content_name":content.name}), content.name)]

    rendered_content = u''
    unparsed_content = re.split(r"\r\n|\r|\n", content.content)

    parser = content_parser.ContentParser(iter(unparsed_content))
    parser.set_fileroot(kwargs["media_root"])
    for line in parser.parse():
        # Embed a file or page (TODO: Use custom template tags for a nicer solution)
        include_file_re = re.match("{{\s+(?P<filename>.+)\s+}}", line)
        if include_file_re:
            # It's an embedded source code file
            if include_file_re.group("filename") == parser.get_current_filename():
                # Read the embedded file into file_contents, then syntax highlight it, then replace the placeholder with the contents
                from pygments import highlight
                from pygments.lexers import PythonLexer
                from pygments.formatters import HtmlFormatter
                file_contents = codecs.open(File.objects.get(name=include_file_re.group("filename")).fileinfo.path, "r", "utf-8").read()
                file_contents = highlight(file_contents, PythonLexer(), HtmlFormatter(nowrap=True))
                #file_contents = codecs.open(os.path.join(kwargs["media_root"], course_name, include_file_re.group("filename")), "r", "utf-8").read()
                line = line.replace(include_file_re.group(0), file_contents)
            # It's an embedded task
            elif include_file_re.group("filename") == parser.get_current_taskname():
                embedded_content = ContentPage.objects.get(incarnation=selected_incarnation.id, name=parser.get_current_taskname())
                pages.append(embedded_content)
                unparsed_embedded_content = re.split(r"\r\n|\r|\n", embedded_content.content)
                embedded_parser = content_parser.ContentParser(iter(unparsed_embedded_content))
                rendered_em_content = u''
                for emline in embedded_parser.parse():
                    rendered_em_content += emline
                
                # use template here to render to rendered_em_content
                emb_tasktype, emb_question, emb_choices = get_task_info(embedded_content)
                emb_t = loader.get_template("courses/task.html")
                emb_c = RequestContext(request, {
                        'emb_content': rendered_em_content,
                        'content_name': embedded_content.name,
                        'content_name_id': embedded_content.name.replace(" ", "_"),
                        'tasktype': emb_tasktype,
                        'question': emb_question,
                        'choices': emb_choices,
                })
                rendered_em_content = emb_t.render(emb_c)

                line = line.replace(include_file_re.group(0), rendered_em_content)
                
        rendered_content += line
    
    tasktype, question, choices = get_task_info(content)

    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course': selected_course,
        'incarnation': selected_incarnation,
        'content': rendered_content,
        'content_name': content.name,
        'content_name_id': content.name.replace(" ", "_"),
        'navurls': navurls,
        'title': '%s - %s' % (content.name, selected_course.name),
        'answer_check_url': reverse('courses.views.incarnation', kwargs={"course_name":course_name, "incarnation_name":incarnation_name}),
        'tasktype': tasktype,
        'question': question,
        'choices': choices,
    })
    return HttpResponse(t.render(c))

def file_download(request, course_name, filename, **kwargs):
    import os
    import mimetypes

    file_path = File.objects.get(name=filename).fileinfo.path
    mimetypes.init()
    try:
        #file_path = os.path.join(kwargs["media_root"], course_name, filename)
        fd = open(file_path, "rb")
        mime_type_guess = mimetypes.guess_type(file_path)
        response = HttpResponse(fd, mime_type_guess[0])
        return response
    except IOError:
        return Http404()

