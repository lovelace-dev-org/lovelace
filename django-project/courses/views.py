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

    # # Build the course content tree

    #node_ids = [id['id'] for id in course_graph_nodes.values('id')]
    #parent_node_ids = [id['parentnode_id'] for id in course_graph_nodes.values('parentnode_id')]
    # end_ids = set(node_ids) - set(parent_node_ids)

    # course_tree = Tree()
    # list_tree = []
    # visited_nodes = {}
    # saved_starting_nodes = []
    # for end_id in end_ids:
    #     node = Node(end_id, [])

    #     node_start_found = False
    #     nop_loop = False

    #     current_id = end_id
    #     lnode = [current_id]
    #     visited_nodes[current_id] = lnode

    #     while not node_start_found:
    #         parent_id = course_graph_nodes.get(id=current_id).parentnode_id
    #         if not parent_id:
    #             break
    #         if nop_loop:
    #             lnode = visited_nodes[parent_id]
    #         elif parent_id not in visited_nodes.keys():
    #             node = node.addParent(parent_id)
    #             lnode = [parent_id, lnode]
    #             visited_nodes[parent_id] = lnode
    #         else:
    #             visited_nodes[parent_id].append(lnode)
    #             lnode = visited_nodes[parent_id]
    #             nop_loop = True
    #         current_id = parent_id

    #     course_tree.addNode(node)
    #     if lnode[0] not in saved_starting_nodes:
    #         list_tree.append(lnode)
    #         saved_starting_nodes.append(lnode[0])

    # get_content = lambda x: content_list.get(id=course_graph_nodes.get(id=x).content_id)
    # tree = traverse_tree(list_tree)

    # print tree

    # for n, item in enumerate(tree[::]):
    #     if item == '<' or item == '>':
    #         tree[n] = item
    #     else:
    #         tree[n] = get_content(str(item))

            
#    tree = [get_content(str(x)) for x in tree if str(x) != "<" and str(x) != ">"]
#    tree = [content_list.get(course_graph_nodes.get(str(id)).content_id) for id in tree if str(id) != "<" and str(id) != ">"]

#    print tree

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

def content(request, course_name, incarnation_name, content_name, **kwargs):
    import re
    import codecs
    import os

    selected_course = Course.objects.get(name=course_name)
    selected_incarnation = Incarnation.objects.get(course=selected_course.id, name=incarnation_name)
    content = ContentPage.objects.get(incarnation=selected_incarnation.id, name=content_name)

    # Validate the answer
    if request.POST:
        question = TaskPage.objects.get(id=content.id).question

        correct = False
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
                if request.POST[str(choice.id)] == "true" and choice.correct == True:
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
                if request.POST[str(choice.id)] == "true" and choice.correct == True:
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
                    if re.match(answer.answer, given) and answer.correct:
                        correct = True
                        break
                    elif re.match(answer.answer, given) and not answer.correct:
                        correct = False
                else:
                    if given == answer.answer and answer.correct:
                        correct = True
                        break
                    elif given == answer.answer and not answer.correct:
                        correct = False
                        if answer.hint:
                            hints.append(answer.hint)

        if correct:
            response_string = u"Correct!"
        else:
            response_string = u"Incorrect answer.<br />"
            if hints:
                response_string += "<br />".join(hints)

        response = HttpResponse(response_string)
        return response


    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Courses
               NavURL(reverse('courses.views.course', kwargs={"course_name":course_name}), course_name),
               NavURL(reverse('courses.views.incarnation', kwargs={"course_name":course_name, "incarnation_name":incarnation_name}), incarnation_name),
               NavURL(reverse('courses.views.content', kwargs={"course_name":course_name, "incarnation_name":incarnation_name, "content_name":content.name}), content.name)]

    rendered_content = u''
    unparsed_content = re.split(r"\r\n|\r|\n", content.content)

    parser = content_parser.ContentParser(iter(unparsed_content))
    parser.set_fileroot(kwargs["media_root"])
    for line in parser.parse():
        include_file_re = re.match("{{\s+(?P<filename>.+)\s+}}", line)
        if include_file_re:
            if include_file_re.group("filename") == parser.get_current_filename():
                file_contents = codecs.open(File.objects.get(name=include_file_re.group("filename")).fileinfo.path, "r", "utf-8").read()
                #file_contents = codecs.open(os.path.join(kwargs["media_root"], course_name, include_file_re.group("filename")), "r", "utf-8").read()
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
        'answer_check_url': reverse('courses.views.content', kwargs={"course_name":course_name, "incarnation_name":incarnation_name, "content_name":content.name}),
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

