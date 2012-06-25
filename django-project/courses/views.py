"""
Django views.
TODO: Heavy commenting!
"""
import datetime

from django.http import HttpResponse
from django.template import Context, RequestContext, loader
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.utils import timezone

from courses.models import *

import content_parser
import filecheck_client

class NavURL:
    def __init__(self, url, name):
        self.url = url
        self.name = name

def index(request):
    course_list = Training.objects.all()
    navurls = [NavURL(reverse('courses.views.index'), "Training home")] # Courses
    t = loader.get_template("courses/index.html")
    c = RequestContext(request, {
        'course_list': course_list,
        'navurls': navurls,
        'title': 'Available trainings',
    })
    return HttpResponse(t.render(c))

def training_b(request, course_name):
    selected_course = Training.objects.get(name=course_name)

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

import graph_builder

def add_tree(nodelist,id):
	nodelist.append(ContentGraph.objects.get(id=id))
	for child in ContentGraph.objects.filter(parentnode_id=id):
		add_tree(nodelist,child.id)

def course_graph(request, training_name):
    import codecs
    import os
    selected_course = Training.objects.get(name=training_name)
    topnodes = selected_course.contents.all()
    course_graph_nodes = [] 
    for node in topnodes:
	add_tree(course_graph_nodes,node.id)

    nodes = []
    edges = []
    root_node = graph_builder.Node({"name":"start","shape":"point","width":"0.1","height":"0.1"})
    nodes.append(root_node)
    for graph_node in course_graph_nodes:
        #node = graph_builder.Node(graph_node)
        content = ContentPage.objects.get(id=graph_node.content_id)
        node_url = reverse('courses.views.content', kwargs={"training_name":training_name, "content_id":content.id})
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
    #uncompiled_graph = codecs.open("uncompiled.vg", "w", "utf-8")
    uncompiled_graph = codecs.open("/local/django/raippa_ng/courses/uncompiled.vg", "w", "utf-8")
    uncompiled_graph.write("digraph course_graph {\n")
    uncompiled_graph.write('    node [penwidth="2",fixedsize="True",width="1.6",height="0.5"]\n')
    for node in graph.nodes:
        uncompiled_graph.write("    %s\n" % (node))
    for edge in graph.edges:
        uncompiled_graph.write("    %s\n" % (edge))
    uncompiled_graph.write("}\n")
    uncompiled_graph.close()

    #os.system("dot uncompiled.vg -Txdot -ograph.vg")
    os.system("/usr/bin/dot /local/django/raippa_ng/courses/uncompiled.vg -Txdot -o/local/django/raippa_ng/courses/graph.vg")

    #graph_file = codecs.open("graph.vg", "r", "utf-8")
    graph_file = codecs.open("/local/django/raippa_ng/courses/graph.vg", "r", "utf-8")
    #graph_file = codecs.open("uncompiled.vg", "r", "utf-8") # to debug the uncompile dot file

    # http://stackoverflow.com/questions/908258/generating-file-to-download-with-django
    response = HttpResponse(FileWrapper(graph_file), content_type='text/plain')
    #response['Content-Disposition'] = 'attachment; filename=graph.vg'
    return response
 
def training(request, training_name,**kwargs):
    from django.utils.safestring import mark_safe
    selected_course = Training.objects.get(name=training_name)
    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Course
               NavURL(reverse('courses.views.training', kwargs={"training_name":training_name}), training_name),]

    course_graph_url = reverse('courses.views.course_graph', kwargs={'training_name':training_name})
    frontpage = selected_course.frontpage

    if not frontpage is None:
    	contentid = frontpage.id 
	check_for_answer(request,contentid)
	contextdict = get_content(contentid,selected_course,request,kwargs)
    else:
	contextdict = {}

    contextdict["training"] = selected_course 
    contextdict["course_graph_url"] = course_graph_url
    contextdict["navurls"] = navurls 
    contextdict["title"] = '%s' % selected_course.name

    contents = selected_course.contents.all()
    if len(contents) > 0:
    	tree = []    
        tree.append(mark_safe('>'))
	for C in contents:
		dirtree(tree,C)
        tree.append(mark_safe('<'))
    	contextdict["content_tree"] = tree

    t = loader.get_template("courses/index.html")
    c = RequestContext(request, contextdict)
    return HttpResponse(t.render(c))

def dirtree(tree,node):
    	from django.utils.safestring import mark_safe
	tree.append(node.content)
	kids = ContentGraph.objects.filter(parentnode=node)
	if len(kids) > 0:
            	tree.append(mark_safe('>'))
		for K in kids:
			dirtree(tree,K)
            	tree.append(mark_safe('<'))

	

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


def content(request, training_name, content_name, **kwargs):
    import re
    import codecs
    import os

    print "Ollaan contentissa."

    selected_course = Training.objects.get(name=training_name)
    content = ContentPage.objects.get(name=content_name)
    pages = [content]

    # Validate an answer to question
    if request.method == "POST":
        print "Flow @ content view POST data check"
        question = TaskPage.objects.get(id=content.id).question

        correct = True
        tasktype = None
        choices = None
        answers = None
        hints = []

        # TODO: Create an abstracted answer checking mechanism
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
                    chosen = choice
                elif request.POST[str(choice.id)] == "false" and choice.correct == True:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)
                elif request.POST[str(choice.id)] == "true" and choice.correct == False:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)
                    chosen = choice
                    break
            
            rb_evaluation = Evaluation(points=1.0,feedback="jee")
            rb_evaluation.save()
            rb_answer = UserRadiobuttonTaskAnswer(task=content.taskpage.radiobuttontask, chosen_answer=chosen, evaluation=rb_evaluation,
                                                  user=request.user, answer_date=timezone.now())
            rb_answer.save()

        try:
            if content.taskpage.checkboxtask:
                choices = CheckboxTaskAnswer.objects.filter(task=content.id)
                tasktype = "checkbox"
        except ContentPage.DoesNotExist as e:
            pass

        if choices and tasktype == "checkbox":
            chosen = []
            for choice in choices:
                if request.POST[str(choice.id)] == "true" and choice.correct == True and correct == True:
                    correct = True
                    chosen.append(choice)
                elif request.POST[str(choice.id)] == "false" and choice.correct == True:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)
                elif request.POST[str(choice.id)] == "true" and choice.correct == False:
                    correct = False
                    if choice.hint:
                        hints.append(choice.hint)
                    chosen.append(choice)

            cb_evaluation = Evaluation(points=1.0,feedback="jee")
            cb_evaluation.save()
            cb_answer = UserCheckboxTaskAnswer(task=content.taskpage.checkboxtask, evaluation=cb_evaluation,
                                               user=request.user, answer_date=timezone.now())
            cb_answer.save()
            cb_answer.chosen_answers.add(*chosen)
            cb_answer.save()


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

            tf_evaluation = Evaluation(points=1.0,feedback="jee")
            tf_evaluation.save()
            tf_answer = UserTextfieldTaskAnswer(task=content.taskpage.textfieldtask, given_answer=given, evaluation=tf_evaluation,
                                                user=request.user, answer_date=timezone.now())
            tf_answer.save()
        
        try:
            if content.taskpage.filetask:
                tasktype = "filetask"
        except ContentPage.DoesNotExist as e:
            pass

        if tasktype == "filetask":
            f_returnable = FileTaskReturnable(run_time=datetime.time(0,0,1,500), output="asdf", errors="asdf")
            f_returnable.save()
            f_evaluation = Evaluation(points=1.0,feedback="jee")
            f_evaluation.save()
            f_answer = UserFileTaskAnswer(task=content.taskpage.filetask, returnable=f_returnable, evaluation=f_evaluation,
                                          user=request.user, answer_date=timezone.now())
            f_answer.save()

            for entry_name, uploaded_file in request.FILES.iteritems():
                print "Contents of file '%s':" % (uploaded_file.name)
                f_filetaskreturnfile = FileTaskReturnFile(fileinfo=uploaded_file, returnable=f_returnable)
                f_filetaskreturnfile.save()

                #with open("returnables/%s/%04d/%s" % (user_id, version, uploaded_file.name), "wb+") as destination:
                if uploaded_file.multiple_chunks():
                    for chunk in uploaded_file.chunks():
                        print chunk,
                        #destination.write(chunk)
                else:
                    print uploaded_file.read()
                    #destination.write(uploaded_file.read())
            
            results = filecheck_client.check_file_answer(f_answer)
            print results
            import difflib
            received_output = results["output"].split("\n")
            expected_output = results["ref_output"].split("\n")
            difftable = difflib.HtmlDiff().make_table(fromlines=received_output,tolines=expected_output,fromdesc="Your program's output",todesc="Expected output")
            return HttpResponse(difftable)

        # TODO: Use a template here to make it look nicer.
        if correct:
            response_string = u"Correct!"
        else:
            # TODO: Account for the video hints!
            response_string = u"Incorrect answer.<br />"
            if hints:
                import random
                random.shuffle(hints)
                response_string += "<br />".join(hints)

        response = HttpResponse(response_string)
        return response

    # back to normal flow (representing a content page)

    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Courses
               NavURL(reverse('courses.views.training', kwargs={"training_name":training_name}), training_name),
               NavURL(reverse('courses.views.content', kwargs={"training_name":training_name, "content_name":content.name}), content.name)]

    rendered_content = u''
    unparsed_content = re.split(r"\r\n|\r|\n", content.content)

    parser = content_parser.ContentParser(iter(unparsed_content))
    parser.set_fileroot(kwargs["media_root"])
    parser.set_mediaurl(kwargs["media_url"])
    parser.set_coursename(training_name)
    for line in parser.parse():
        # Embed a file, page or a video (TODO: Use custom template tags for a nicer solution)
        include_file_re = re.search("{{\s+(?P<filename>.+)\s+}}", line)
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
            # It's an embedded video
            elif include_file_re.group("filename") == parser.get_current_videoname():
                video = Video.objects.get(name=parser.get_current_videoname()).link
                line = line.replace(include_file_re.group(0), video)
            # It's an embedded image
            elif include_file_re.group("filename") == parser.get_current_imagename():
                image = Image.objects.get(name=parser.get_current_imagename()).fileinfo.url
                line = line.replace(include_file_re.group(0), image)
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
        'training': selected_course,
        'content': rendered_content,
        'content_name': content.name,
        'content_name_id': content.name,
        'navurls': navurls,
        'title': '%s - %s' % (content.name, selected_course.name),
        'answer_check_url': reverse('courses.views.training', kwargs={"training_name":training_name}),
        'tasktype': tasktype,
        'question': question,
        'choices': choices,
    })
    return HttpResponse(t.render(c))

def user(request, user_name):
    '''Shows user information to the requesting user. The amount of information depends on who the
    requesting user is.'''
    if request.user == "AnonymousUser":
        # TODO: Don't allow anons to view anything
        # Return 404 even if the users exists to prevent snooping around
        # Distinguishing 403 and 404 here would give away information
        return Http404()
    elif request.user == user_name:
        # TODO: Allow the user to view their own info and edit some of it
        pass
    elif request.user == "mdf":
        # TODO: Allow admins to view useful information regarding the user they've requested
        pass
    else:
        # TODO: Allow normal users to view some very basic information?
        pass
    
    checkboxtask_answers = UserCheckboxTaskAnswer.objects.filter(user=request.user)
    radiobuttontask_answers = UserRadiobuttonTaskAnswer.objects.filter(user=request.user)
    textfieldtask_answers = UserTextfieldTaskAnswer.objects.filter(user=request.user)
    filetask_answers = UserFileTaskAnswer.objects.filter(user=request.user)

    t = loader.get_template("courses/userinfo.html")
    c = RequestContext(request, {
        'checkboxtask_answers': checkboxtask_answers,
        'radiobuttontask_answers': radiobuttontask_answers,
        'textfieldtask_answers': textfieldtask_answers,
        'filetask_answers': filetask_answers,
    })
    return HttpResponse(t.render(c))

def file_download(request, filename, **kwargs):
    import os
    import mimetypes

    file_path = File.objects.get(name=filename).fileinfo.path
    mimetypes.init()
    # TODO: Check user rights!
    try:
        #file_path = os.path.join(kwargs["media_root"], course_name, filename)
        fd = open(file_path, "rb")
        mime_type_guess = mimetypes.guess_type(file_path)
        response = HttpResponse(fd, mime_type_guess[0])
        return response
    except IOError:
        return Http404()


def check_for_answer(request,content_id):
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



def get_content(content_id,training,request,kwargs):
    import re
    import codecs
    import os

    content = ContentPage.objects.get(id=content_id)
    pages = [content]

    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Courses
               NavURL(reverse('courses.views.training', kwargs={"training_name":training.name}), training.name),
               NavURL(reverse('courses.views.content', kwargs={"training_name":training.name, "content_name":content.name}), content.name)]

    rendered_content = u''
    unparsed_content = re.split(r"\r\n|\r|\n", content.content)

    parser = content_parser.ContentParser(iter(unparsed_content))
    parser.set_fileroot(kwargs["media_root"])
    parser.set_mediaurl(kwargs["media_url"])
    parser.set_coursename(training)
    for line in parser.parse():
        # Embed a file, page or a video (TODO: Use custom template tags for a nicer solution)
        include_file_re = re.search("{{\s+(?P<filename>.+)\s+}}", line)
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
            # It's an embedded video
            elif include_file_re.group("filename") == parser.get_current_videoname():
                video = Video.objects.get(name=parser.get_current_videoname()).link
                line = line.replace(include_file_re.group(0), video)
            # It's an embedded image
            elif include_file_re.group("filename") == parser.get_current_imagename():
                image = Image.objects.get(name=parser.get_current_imagename()).fileinfo.url
                line = line.replace(include_file_re.group(0), image)
            # It's an embedded task
            elif include_file_re.group("filename") == parser.get_current_taskname():
                #embedded_content = ContentPage.objects.get(incarnation=selected_incarnation.id, name=parser.get_current_taskname())
                embedded_content = ContentPage.objects.get(name=parser.get_current_taskname())
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

    pagedict = {
        'training': training,
        'content': rendered_content,
        'content_name': content.name,
        'content_name_id': content.id, #name.replace(" ", "_"),
        'navurls': navurls,
        'title': '%s - %s' % (content.name, training.name),
        'answer_check_url': reverse('courses.views.training', kwargs={"training_name":training.name}),
        'tasktype': tasktype,
        'question': question,
        'choices': choices,
    }
    return pagedict

