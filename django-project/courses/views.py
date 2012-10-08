"""
Django views.
TODO: Heavy commenting!
TODO: Use classes instead of bare functions to group data!
"""
import os
import re
import sre_constants
import codecs
import random
import difflib
import datetime
import mimetypes
from cgi import escape

from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.template import Context, RequestContext, loader
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.utils import timezone
from django.utils.safestring import mark_safe

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

from courses.models import *

import content_parser
import blockparser
import filecheck_client
import graph_builder

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

def add_tree(nodelist,id):
    nodelist.append(ContentGraph.objects.get(id=id))
    for child in ContentGraph.objects.filter(parentnode_id=id):
        add_tree(nodelist,child.id)

def course_graph(request, training_name):
    # TODO: Use temporary files and/or dynamic root directory!
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
 
def training(request, training_name, **kwargs):
    selected_course = Training.objects.get(name=training_name)
    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Course
               NavURL(reverse('courses.views.training', kwargs={"training_name":training_name}), training_name),]

    course_graph_url = reverse('courses.views.course_graph', kwargs={'training_name':training_name})
    frontpage = selected_course.frontpage

    if frontpage:
    	content_name = frontpage.url_name
        kwargs["frontpage"] = True
	contextdict = content(request, training_name, content_name, **kwargs)
    else:
	contextdict = {}

    contextdict["training"] = selected_course 
    contextdict["course_graph_url"] = course_graph_url
    contextdict["navurls"] = navurls 
    contextdict["title"] = '%s' % selected_course.name

    contents = selected_course.contents.all().order_by('parentnode', '-id')
    if len(contents) > 0:
        tree = []    
        tree.append((mark_safe('>'), None))
        for content_ in contents:
            dirtree(tree, content_, request.user)
        tree.append((mark_safe('<'), None))
        contextdict["content_tree"] = tree

    t = loader.get_template("courses/index.html")
    c = RequestContext(request, contextdict)
    return HttpResponse(t.render(c))

def dirtree(tree, node, user):
    result = "not_answered"
    if user.is_authenticated():
#        if user.username == "mdf" or user.username == "testimdf":
        evaluations = None
        try:
            if not evaluations: evaluations = Evaluation.objects.filter(useranswer__usercheckboxtaskanswer__task=node.content, useranswer__user=user)
        except ContentPage.DoesNotExist:
            pass
        try:
            if not evaluations: evaluations = Evaluation.objects.filter(useranswer__userradiobuttontaskanswer__task=node.content, useranswer__user=user)
        except ContentPage.DoesNotExist:
            pass
        try:
            if not evaluations: evaluations = Evaluation.objects.filter(useranswer__usertextfieldtaskanswer__task=node.content, useranswer__user=user)
        except ContentPage.DoesNotExist:
            pass
        try:
            if not evaluations: evaluations = Evaluation.objects.filter(useranswer__userfiletaskanswer__task=node.content, useranswer__user=user)
        except ContentPage.DoesNotExist:
            pass

        if not evaluations:
            result = "not_answered"
        else:
            correct = evaluations.filter(points__gt=0.0)
            if correct:
                result = "correct"
            else:
                result = "incorrect"

    list_item = (node.content, result)
    if list_item not in tree:
        tree.append(list_item)

    children = ContentGraph.objects.filter(parentnode=node)
    if len(children) > 0:
        tree.append((mark_safe('>'), None))
        for child in children:
            dirtree(tree, child, user)
        tree.append((mark_safe('<'), None))

def get_task_info(content):
    tasktype = None
    question = None
    choices = None
    answers = None
    try:
        if content.taskpage.radiobuttontask:
            tasktype = "radiobutton"
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
            answers = TextfieldTaskAnswer.objects.filter(task=content.id)
            question = TaskPage.objects.get(id=content.id).question
    except ContentPage.DoesNotExist as e:
        pass

    try:
        if content.taskpage.filetask:
            tasktype = "file"
            question = TaskPage.objects.get(id=content.id).question
    except ContentPage.DoesNotExist as e:
        pass

    return (tasktype, question, choices, answers)

def radiobutton_task_check(content, user, choices, post_data):
    points = 0.0

    # Determine, if the given answer was correct and which hints to show
    correct = True
    hints = []
    comments = []
    for choice in choices:
        if post_data[str(choice.id)] == "true":
            chosen = choice

        if post_data[str(choice.id)] == "true" and choice.correct == True and correct == True:
            correct = True
            if choice.comment:
                comments.append(choice.comment)
        elif post_data[str(choice.id)] == "false" and choice.correct == True:
            correct = False
            if choice.hint:
                hints.append(choice.hint)
        elif post_data[str(choice.id)] == "true" and choice.correct == False:
            correct = False
            if choice.hint:
                hints.append(choice.hint)
            if choice.comment:
                comments.append(choice.comment)
            break
    
    # Save the results to the database, if the question was answered by a non-anonymous user
    if user.is_authenticated():
        if correct:
            points = 1.0
        rb_evaluation = Evaluation(points=points,feedback="",correct=correct)
        rb_evaluation.save()
        rb_answer = UserRadiobuttonTaskAnswer(task=content.taskpage.radiobuttontask, chosen_answer=chosen, evaluation=rb_evaluation,
                                              user=user, answer_date=timezone.now())
        rb_answer.save()
    
    return correct, hints, comments

def checkbox_task_check(content, user, choices, post_data):
    points = 0.0

    # Determine, if the given answer was correct and which hints to show
    correct = True
    hints = []
    comments = []
    chosen = []
    for choice in choices:
        if post_data[str(choice.id)] == "true" and choice.correct == True and correct == True:
            correct = True
            chosen.append(choice)
            if choice.comment:
                comments.append(choice.comment)
        elif post_data[str(choice.id)] == "false" and choice.correct == True:
            correct = False
            if choice.hint:
                hints.append(choice.hint)
        elif post_data[str(choice.id)] == "true" and choice.correct == False:
            correct = False
            if choice.hint:
                hints.append(choice.hint)
            if choice.comment:
                comments.append(choice.comment)
            chosen.append(choice)

    # Save the results to the database, if the question was answered by a non-anonymous user
    if user.is_authenticated():
        if correct:
            points = 1.0
        cb_evaluation = Evaluation(points=points,feedback="",correct=correct)
        cb_evaluation.save()
        cb_answer = UserCheckboxTaskAnswer(task=content.taskpage.checkboxtask, evaluation=cb_evaluation,
                                           user=user, answer_date=timezone.now())
        cb_answer.save()
        cb_answer.chosen_answers.add(*chosen)
        cb_answer.save()

    return correct, hints, comments

def textfield_task_check(content, user, answers, post_data):
    points = 0.0

    # Determine, if the given answer was correct and which hints to show
    correct = True
    hints = []
    comments = []
    errors = []
    given = post_data["answer"].replace("\r\n", "\n").replace("\n\r", "\n")
    for answer in answers:
        if answer.regexp:
            try:
                if re.match(answer.answer, given) and answer.correct and correct == True:
                    correct = True
                    if answer.comment:
                        comments.append(answer.comment)
                    break
                elif re.match(answer.answer, given) and not answer.correct:
                    correct = False
                    if answer.hint:
                        hints.append(answer.hint)
                    if answer.comment:
                        comments.append(answer.comment)
                elif not re.match(answer.answer, given) and answer.correct:
                    correct = False
                    if answer.hint:
                        hints.append(answer.hint)
            except sre_constants.error, e_msg:
                errors.append("Contact staff, regexp error: " + e_msg)
                correct = False
        else:
            if given == answer.answer and answer.correct and correct == True:
                correct = True
                if answer.comment:
                    comments.append(answer.comment)
                break
            elif given == answer.answer and not answer.correct:
                correct = False
                if answer.hint:
                    hints.append(answer.hint)
                if answer.comment:
                    comments.append(answer.comment)
            elif given != answer.answer and answer.correct:
                correct = False
                if answer.hint:
                    hints.append(answer.hint)

    # Save the results to the database, if the question was answered by a non-anonymous user
    if user.is_authenticated():
        if correct:
            points = 1.0
        tf_evaluation = Evaluation(points=points,feedback="",correct=correct)
        tf_evaluation.save()
        tf_answer = UserTextfieldTaskAnswer(task=content.taskpage.textfieldtask, given_answer=given, evaluation=tf_evaluation,
                                            user=user, answer_date=timezone.now())
        tf_answer.save()

    return correct, hints, comments, errors

def file_task_check(content, user, files_data, post_data):
    points = 0.0
    correct = True
    hints = []
    comments = []

    if user.is_authenticated():
        # TODO: Fix the information that will be saved
        f_returnable = FileTaskReturnable(run_time=datetime.time(0,0,1,500), output="filler-output-filler", errors="filler-errors-filler", retval=0)
        f_returnable.save()
        f_evaluation = Evaluation(points=points,feedback="",correct=False)
        f_evaluation.save()
        if "collaborators" in post_data.keys():
            collaborators = post_data["collaborators"]
        else:
            collaborators = None
        print collaborators
        f_answer = UserFileTaskAnswer(task=content.taskpage.filetask, returnable=f_returnable, evaluation=f_evaluation,
                                      user=user, answer_date=timezone.now(), collaborators=collaborators)
        f_answer.save()

        for entry_name, uploaded_file in files_data.iteritems():
            f_filetaskreturnfile = FileTaskReturnFile(fileinfo=uploaded_file, returnable=f_returnable)
            f_filetaskreturnfile.save()
        
        results = filecheck_client.check_file_answer(task=content.taskpage.filetask, files={}, answer=f_answer)

        # Quickly determine, whether the answer was correct
        results_zipped = []
        student_results = []
        reference_results = []
        ref = ""
        if "reference" in results.keys():
            ref = "reference"
        elif "expected" in results.keys():
            ref = "expected"

        for test in results["student"].iterkeys():
            # TODO: Do the output and stderr comparison here instead of below
            results_zipped.append(zip(results["student"][test]["outputs"], results[ref][test]["outputs"]))
            results_zipped.append(zip(results["student"][test]["errors"], results[ref][test]["errors"]))

            for name, content in results[ref][test]["outputfiles"].iteritems():
                if name not in results["student"][test]["outputfiles"].iterkeys():
                    correct = False
                else:
                    if content != results["student"][test]["outputfiles"][name]:
                        correct = False

        for test in results_zipped:
            for resultpair in test:
                print resultpair
                if resultpair[0].replace('\r\n', '\n') != resultpair[1].replace('\r\n', '\n'):
                    correct = False

        if correct:
            f_evaluation.points = 1.0
            f_evaluation.correct = correct
            f_evaluation.save()
            f_answer.save()
    else:
        print "Blaa?"
        files = {}
        print files_data
        for rf in files_data.itervalues():
            f = ""
            for chunk in rf.chunks():
                f += chunk
            files[rf.name] = f
        results = filecheck_client.check_file_answer(task=content.taskpage.filetask, files=files)

        # Quickly determine, whether the answer was correct
        results_zipped = []
        student_results = []
        reference_results = []
        for test in results["student"].iterkeys():
            results_zipped.append(zip(results["student"][test]["outputs"], results["reference"][test]["outputs"]))

        for test in results_zipped:
            print test
            for resultpair in test:
                if resultpair[0] != resultpair[1]:
                    correct = False
        print results

    # Get a nice HTML table for the diffs
    diff_table = filecheck_client.html(results)

    return correct, hints, comments, diff_table

def check_answer(request, training_name, content_name, **kwargs):
    print u"Ollaan tehtavan tarkistuksessa"
    # Validate an answer to question
    if request.method == "POST":
        pass
    else:
        return HttpResponse("")

    selected_course = Training.objects.get(name=training_name)
    content = ContentPage.objects.get(url_name=content_name)

    # Check if a deadline exists and if we are past it
    training = Training.objects.get(name=training_name)
    try:
        content_graph = training.contents.get(content=content)
    except ContentGraph.DoesNotExist as e:
        pass
    else:
        if not content_graph.deadline or datetime.datetime.now() < content_graph.deadline:
            pass
        else:
            # TODO: Use a template!
            return HttpResponse("The deadline for this task (%s) has passed. Your answer will not be evaluated!" % (content_graph.deadline))

    tasktype, question, choices, answers = get_task_info(content)

    correct = True
    hints = []
    comments = []
    errors = []
    diff_table = ""

    if choices and tasktype == "radiobutton":
        correct, hints, comments = radiobutton_task_check(content, request.user, choices, request.POST)
    elif choices and tasktype == "checkbox":
        correct, hints, comments = checkbox_task_check(content, request.user, choices, request.POST)
    elif answers and tasktype == "textfield":
        correct, hints, comments, errors = textfield_task_check(content, request.user, answers, request.POST)
    elif tasktype == "file":
        correct, hints, comments, diff_table = file_task_check(content, request.user, request.FILES, request.POST)

    # Compile the information required for the task evaluation
    if correct:
        evaluation = u"Correct!"
    else:
        # TODO: Account for the video hints!
        evaluation = u"Incorrect answer."
        if hints:
            random.shuffle(hints)

    r_diff_table = u""
    try:
        r_diff_table = unicode(diff_table, "utf-8")
    except UnicodeDecodeError:
        r_diff_table = unicode(diff_table, "iso-8859-1")

    t = loader.get_template("courses/task_evaluation.html")
    c = Context({
        'evaluation': evaluation,
        'errors': errors,
        'hints': hints,
        'comments': comments,
        'diff_table': r_diff_table,
    })

    return HttpResponse(t.render(c))

def get_user_task_info(user, task, tasktype):
    evaluations = None
    if tasktype == "checkbox":
        if not evaluations: evaluations = Evaluation.objects.filter(useranswer__usercheckboxtaskanswer__task=task, useranswer__user=user)
    elif tasktype == "radiobutton":
        if not evaluations: evaluations = Evaluation.objects.filter(useranswer__userradiobuttontaskanswer__task=task, useranswer__user=user)
    elif tasktype == "textfield":
        if not evaluations: evaluations = Evaluation.objects.filter(useranswer__usertextfieldtaskanswer__task=task, useranswer__user=user)
    elif tasktype == "file":
        if not evaluations: evaluations = Evaluation.objects.filter(useranswer__userfiletaskanswer__task=task, useranswer__user=user)

    if not evaluations:
        result = "not_answered"
    else:
        correct = evaluations.filter(correct=True)
        if correct:
            result = "correct"
        else:
            result = "incorrect"

    return result

def content(request, training_name, content_name, **kwargs):
    print "Ollaan contentissa."

    selected_course = Training.objects.get(name=training_name)
    content = ContentPage.objects.get(url_name=content_name)
    pages = [content]

    tasktype, question, choices, answers = get_task_info(content)
    if request.user.is_authenticated():
        task_evaluation = get_user_task_info(request.user, content, tasktype)
    else:
        task_evaluation = None

    try:
        question = blockparser.parseblock(escape(question))
    except TypeError: # It was NoneType
        pass
    except AttributeError: # It was NoneType
        pass

    emb_tasktype = None
    contains_embedded_task = False

    navurls = [NavURL(reverse('courses.views.index'), "Training home"), # Courses
               NavURL(reverse('courses.views.training', kwargs={"training_name":training_name}), training_name),
               NavURL(reverse('courses.views.content', kwargs={"training_name":training_name, "content_name":content.name}), content.name)]

    rendered_content = u''
    unparsed_content = re.split(r"\r\n|\r|\n", content.content)

    parser = content_parser.ContentParser(iter(unparsed_content))
    parser.set_fileroot(kwargs["raippa_root"])
    parser.set_mediaurl(kwargs["media_url"])
    parser.set_coursename(training_name)
    for line in parser.parse():
        # Embed a file, page or a video (TODO: Use custom template tags for a nicer solution)
        include_file_re = re.search("{{\s+(?P<filename>.+)\s+}}", line)
        if include_file_re:
            # It's an embedded source code file
            if include_file_re.group("filename") == parser.get_current_filename():
                # Read the embedded file into file_contents, then syntax highlight it, then replace the placeholder with the contents
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
                print parser.get_current_taskname()
                try:
                    embedded_content = ContentPage.objects.get(url_name=parser.get_current_taskname())
                except ContentPage.DoesNotExist as e:
                    embedded_content = LecturePage()
                    embedded_content.content = u"Embedded content '%s' not found.\n" % (parser.get_current_taskname())
                pages.append(embedded_content)
                unparsed_embedded_content = re.split(r"\r\n|\r|\n", embedded_content.content)
                embedded_parser = content_parser.ContentParser(iter(unparsed_embedded_content))
                rendered_em_content = u''
                for emline in embedded_parser.parse():
                    rendered_em_content += emline
                
                emb_tasktype, emb_question, emb_choices, emb_answers = get_task_info(embedded_content)
                if emb_tasktype:
                    contains_embedded_task = True

                if request.user.is_authenticated():
                    emb_task_evaluation = get_user_task_info(request.user, embedded_content, emb_tasktype)
                else:
                    emb_task_evaluation = None

                try:
                    emb_question = blockparser.parseblock(escape(emb_question))
                except TypeError: # It was NoneType
                    pass
                except AttributeError: # It was NoneType
                    pass

                emb_t = loader.get_template("courses/task.html")
                emb_c = RequestContext(request, {
                    'embedded_task': True,
                    'emb_content': rendered_em_content,
                    'content_name': embedded_content.name,
                    'content_name_id': embedded_content.url_name,
                    'content_urlname': embedded_content.url_name,
                    'answer_check_url': reverse('courses.views.training', kwargs={"training_name":training_name}),
                    'tasktype': emb_tasktype,
                    'question': emb_question,
                    'choices': emb_choices,
                    'evaluation': emb_task_evaluation,
                })
                rendered_em_content = emb_t.render(emb_c)
                line = line.replace(include_file_re.group(0), rendered_em_content)
                
        rendered_content += line
    
    c = RequestContext(request, {
        'embedded_task': False,
        'contains_embedded_task': contains_embedded_task,
        'training': selected_course,
        'content': rendered_content,
        'content_name': content.name,
        'content_name_id': content.url_name,
        'content_urlname': content.url_name,
        'navurls': navurls,
        'title': '%s - %s' % (content.name, selected_course.name),
        'answer_check_url': reverse('courses.views.training', kwargs={"training_name":training_name}),
        'emb_tasktype': emb_tasktype,
        'tasktype': tasktype,
        'question': question,
        'choices': choices,
        'evaluation': task_evaluation,
    })
    if "frontpage" in kwargs:
        return c
    else:
        t = loader.get_template("courses/index.html")
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

def users(request, training_name):
    '''Admin view that shows a table of all users and the tasks they've done on a particular course.'''
    if not request.user.is_authenticated() and not request.user.is_active and not request.user.is_staff:
        return HttpResponseNotFound()

    selected_course = Training.objects.get(name=training_name)
    users = User.objects.all()
    content_nodes = selected_course.contents.all()
    contents = [cn.content for cn in content_nodes]

    user_evaluations = []
    for user in users:
        username = user.username
        db_user_evaluations = Evaluation.objects.filter(useranswer__user=user, points__gt=0.0)
        evaluations = []

        print username

        for content in contents:
            tasktype, question, choices, answers = get_task_info(content)
            if tasktype == "checkbox":
                db_evaluations = db_user_evaluations.filter(useranswer__usercheckboxtaskanswer__task=content)
            elif tasktype == "radiobutton":
                db_evaluations = db_user_evaluations.filter(useranswer__userradiobuttontaskanswer__task=content)
            elif tasktype == "textfield":
                db_evaluations = db_user_evaluations.filter(useranswer__usertextfieldtaskanswer__task=content)
            elif tasktype == "file":
                db_evaluations = db_user_evaluations.filter(useranswer__userfiletaskanswer__task=content)
            else:
                db_evaluations = []

            if db_evaluations:
                evaluations.append(1)
            else:
                evaluations.append(0)
        user_evaluations.append((username, evaluations, sum(evaluations)))

    t = loader.get_template("courses/usertable.html")
    c = RequestContext(request, {
        'training_name':training_name,
        'content_count':len(contents),
        'contents':contents,
        'user_evaluations':user_evaluations,
    })
    return HttpResponse(t.render(c))

def textfield_eval(given, answers):
    given = given.replace("\r\n", "\n").replace("\n\r", "\n")
    correct = True
    hinted = False
    errors = []
    for answer in answers:
        if answer.regexp:
            try:
                if re.match(answer.answer, given) and answer.correct and correct == True:
                    correct = True
                    break
                elif re.match(answer.answer, given) and not answer.correct:
                    correct = False
                    if answer.hint: hinted = True
                elif not re.match(answer.answer, given) and answer.correct:
                    correct = False
            except sre_constants.error, e_msg:
                errors.append("Regexp error: " + e_msg)
                correct = False
        else:
            if given == answer.answer and answer.correct and correct == True:
                correct = True
                break
            elif given == answer.answer and not answer.correct:
                correct = False
                if answer.hint: hinted = True
            elif given != answer.answer and answer.correct:
                correct = False
    return (correct, hinted)

def stats(request, task_name):
    '''Shows statistics on the selected task.'''
    if not request.user.is_authenticated() and not request.user.is_active and not request.user.is_staff:
        return HttpResponseNotFound()

    checkbox_answers = radiobutton_answers = textfield_answers = file_answers = None
    textfield_answers_count = textfield_final = None
    file_answers = file_answers_count = file_user_count = file_correctly_by = None
    radiobutton_answers_count = radiobutton_final = None
    content_page = ContentPage.objects.get(url_name=task_name)
    tasktype, question, choices, answers = get_task_info(content_page)

    if tasktype == "checkbox":
        checkbox_answers = UserCheckboxTaskAnswer.objects.filter(task=content_page)
    elif tasktype == "radiobutton":
        radiobutton_answers = UserRadiobuttonTaskAnswer.objects.filter(task=content_page)
        radiobutton_answers_count = radiobutton_answers.count()
        radiobutton_selected_answers = list(radiobutton_answers.values_list("chosen_answer", flat=True))
        radiobutton_set = set(radiobutton_selected_answers)
        radiobutton_final = []
        for answer in radiobutton_set:
            answer_choice = RadiobuttonTaskAnswer.objects.get(id=answer)
            radiobutton_final.append((answer_choice.answer, radiobutton_selected_answers.count(answer), answer_choice.correct))
    elif tasktype == "textfield":
        textfield_answers = list(UserTextfieldTaskAnswer.objects.filter(task=content_page).values_list("given_answer", flat=True))
        textfield_answers_count = len(textfield_answers)
        textfield_set = set(textfield_answers)
        textfield_final = []
        for answer in textfield_set:
            textfield_final.append((answer, textfield_answers.count(answer),) + textfield_eval(answer, answers))
        textfield_final = sorted(textfield_final, key=lambda x: x[1], reverse=True)
    elif tasktype == "file":
        file_answers = list(UserFileTaskAnswer.objects.filter(task=content_page).values_list("user", flat=True))
        file_answers_count = len(file_answers) # how many times answered
        file_set = set(file_answers)
        file_user_count = len(file_set) # how many different users have answered
        file_correctly_by = 0
        for user in file_set:
            evaluations = Evaluation.objects.filter(useranswer__userfiletaskanswer__task=content_page, useranswer__user=user)
            correct = evaluations.filter(points__gt=0.0)
            if correct: file_correctly_by += 1

    t = loader.get_template("courses/task_stats.html")
    c = RequestContext(request, {
        "content": content_page,
        "question": question,
        "tasktype": tasktype,
        "choices": choices,
        "answers": answers,
        "checkbox_answers": checkbox_answers,

        "radiobutton_answers": radiobutton_answers,
        "radiobutton_answers_count": radiobutton_answers_count,
        "radiobutton_final": radiobutton_final,

        "textfield_answers": textfield_answers,
        "textfield_answers_count": textfield_answers_count,
        "textfield_final": textfield_final,

        "file_answers": file_answers,
        "file_answers_count": file_answers_count,
        "file_user_count": file_user_count,
        "file_correctly_by": file_correctly_by,
    })
    return HttpResponse(t.render(c))

def image_download(request, imagename, **kwargs):
    try:
        file_path = Image.objects.get(name=imagename).fileinfo.path
    except Image.DoesNotExist:
        try:
            file_path = Image.objects.get(fileinfo='images/'+imagename).fileinfo.path
        except Image.DoesNotExist:
            file_path = ""

    mimetypes.init()
    try:
        fd = open(file_path, "rb")
        mime_type_guess = mimetypes.guess_type(file_path)
        response = HttpResponse(fd, mime_type_guess[0])
        return response
    except IOError:
        return HttpResponseNotFound()

def file_download(request, filename, **kwargs):
    try:
        file_path = File.objects.get(name=filename).fileinfo.path
    except File.DoesNotExist:
        try:
            file_path = File.objects.get(fileinfo='files/'+filename).fileinfo.path
        except File.DoesNotExist:
            try:
                file_path = FileTaskTestIncludeFile.objects.get(fileinfo=filename).fileinfo.path
            except File.DoesNotExist:
                file_path = ""

    #file_path = os.path.join(kwargs['media_root'], 'files', filename)
    mimetypes.init()
    # TODO: Check user rights!
    try:
        #file_path = os.path.join(kwargs["media_root"], course_name, filename)
        fd = open(file_path, "rb")
        mime_type_guess = mimetypes.guess_type(file_path)
        response = HttpResponse(fd, mime_type_guess[0])
        #response['Content-Disposition'] = 'attachment; filename=%s' % (filename) # Force download?
        return response
    except IOError:
        return HttpResponseNotFound()
