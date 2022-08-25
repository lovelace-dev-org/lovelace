import base64
from django.template import loader
from courses import markupparser
from utils.archive import get_single_archived, get_archived_instances
from utils.files import get_file_contents_b64
import courses.models as cm


INCORRECT = 0
CORRECT = 1
INFO = 2
ERROR = 3
DEBUG = 4
LINT_C = 10 #10
LINT_R = 11 #11
LINT_W = 12 #12
LINT_E = 13 #13

# NOTE: the amount of reverts caused by this is disgusting.
def file_upload_payload(exercise, student_files, instance, revision=None):
    payload = {
        "resources": {
            "files_to_check": {},
            "checker_files": {}
        },
        "tests": []
    }
    if revision is not None:
        archived = get_archived_instances(exercise, revision)
        exercise = archived["self"]
        tests = archived["fileexercisetest_set"]
        exercise_files = archived["fileexercisetestincludefile_set"]
        instance_file_links = archived["instanceincludefiletoexerciselink_set"]
        # MONKEY PATCH FOR BROKEN ARCHIVED EXERCISES
        if not instance_file_links:
            instance_file_links = exercise.instanceincludefiletoexerciselink_set.get_queryset()
    else:
        tests = exercise.fileexercisetest_set.get_queryset()
        exercise_files = exercise.fileexercisetestincludefile_set.get_queryset()
        instance_file_links = exercise.instanceincludefiletoexerciselink_set.get_queryset()
    
    # Resources
    for a_file in student_files:
        a_file.seek(0)
        payload["resources"]["files_to_check"][a_file.name] = base64.b64encode(a_file.read()).decode("utf-8")
    
    for ex_file in exercise_files:
        payload["resources"]["checker_files"][ex_file.fileinfo.name] = {
            "content": get_file_contents_b64(ex_file),
            "purpose": ex_file.file_settings.purpose,
            "name": ex_file.file_settings.name,
            "chmod": ex_file.file_settings.chmod_settings,
        }
    
    instance_links = instance.instanceincludefiletoinstancelink_set.get_queryset()
    for if_link in instance_file_links:
        ii_link = instance_links.get(include_file=if_link.include_file)
        if ii_link.revision is not None:
            i_file = get_single_archived(if_link.include_file, ii_link.revision)
        else:
            i_file = if_link.include_file
        payload["resources"]["checker_files"][i_file.fileinfo.name] = {
            "content": get_file_contents_b64(i_file),
            "purpose": if_link.file_settings.purpose,
            "name": if_link.file_settings.name,
            "chmod": if_link.file_settings.chmod_settings
        }   
    
    # Tests
    for i, test in enumerate(tests):
        test_payload = {
            "test_id": test.id,
            "required_files": [],
            "stages": [],
            "name": test.name,
        }
        if revision is not None:
            archived = get_archived_instances(test, revision)
            test = archived["self"]
            stages = archived["fileexerciseteststage_set"]
            required_files = archived["required_files"]
            required_instance_files = archived["required_instance_files"]
        else:
            stages = test.fileexerciseteststage_set.get_queryset()
            required_files = test.required_files.all()
            required_instance_files = test.required_instance_files.all()
            
        for req_file in required_files:
            test_payload["required_files"].append(req_file.fileinfo.name)
        for req_file in required_instance_files:
            test_payload["required_files"].append(req_file.fileinfo.name)
            
        for stage in stages:
            if revision is not None:
                archived = get_archived_instances(stage, revision)
                stage = archived["self"]
                commands = archived["fileexercisetestcommand_set"]
            else:
                commands = stage.fileexercisetestcommand_set.all()
                
            command_list = []
            for command in commands:
                command_list.append({
                    "input_text": command.input_text,
                    "return_value": command.return_value,
                    "cmd": command.command_line,
                    "ordinal": command.ordinal_number,
                    "timeout": command.timeout.total_seconds(),
                    "json_output": command.json_output,
                    "stdout": command.significant_stdout,
                    "stderr": command.significant_stderr,
                })
                
            test_payload["stages"].append({
                "id": stage.id,
                "ordinal": stage.ordinal_number,
                "name": stage.name,
                "commands": command_list
            })
        
        payload["tests"].append(test_payload)
        
    return payload


def render_json_feedback(log, request, course, instance):
    """
    Renders execise feedback from the exercise log JSON format. Parses
    messages, hints, triggers, and the final result from the log and returns
    them as a dictionary. 
    
    Messages and hints are ran through the markupparser, which makes it
    possible to include any markup in the log. 
    """

    # render all individual messages in the log tree
    triggers = []
    hints = []
    correct = True

    context = {
        "course_slug": course.slug,
        "instance_slug": instance.slug
    }

    for test in log["tests"]:
        test["title"] = "".join(markupparser.MarkupParser.parse(test["title"], request, context)).strip()
        for run in test["runs"]:
            run["correct"] = True
            for output in run["output"]:
                output["msg"] = "".join(markupparser.MarkupParser.parse(output["msg"], request, context)).strip()
                triggers.extend(output.get("triggers", []))
                hints.extend(
                    "".join(markupparser.MarkupParser.parse(msg, request, context)).strip()
                    for msg in output.get("hints", [])
                )
                if output["flag"] in (INCORRECT, ERROR):
                    run["correct"] = False
                    correct = False

        test["runs"].sort(key=lambda run: run["correct"])


    t_messages = loader.get_template('courses/exercise-evaluation-messages.html')
    t_exercise = loader.get_template("courses/exercise-evaluation.html")
    c_exercise = {
        'evaluation': correct
    }
    feedback = {
        "messages": t_messages.render({'log': log["tests"]}),
        "hints": hints,
        "triggers": triggers,
        "result": t_exercise.render(c_exercise)
    }
    return feedback

def apply_late_rule(evaluation, rule):
    print("applying rule", rule)
    quotient = evaluation.get("points", 0) / evaluation.get("max", 1)
    return eval(rule.format(
        p=evaluation.get("points", 0),
        m=evaluation.get("max", 1),
        q=quotient
    ))


def update_completion(exercise, instance, user, evaluation, answer_date):
    link = cm.EmbeddedLink.objects.filter(
        instance=instance,
        embedded_page=exercise
    ).first()
    parent_graph = link.parent.contentgraph_set.get_queryset().get(instance=instance)
    late = parent_graph.deadline and (answer_date > parent_graph.deadline)
    print(late, parent_graph.late_rule)


    changed = False
    correct = evaluation["evaluation"]
    if correct:
        if late and parent_graph.late_rule:
            quotient = apply_late_rule(evaluation, parent_graph.late_rule)
        else:
            quotient = evaluation.get("points", 0) / evaluation.get("max", 1)
    else:
        quotient = 0

    try:
        completion = cm.UserTaskCompletion.objects.get(
            exercise=exercise,
            instance=instance,
            user=user
        )
    except cm.UserTaskCompletion.DoesNotExist:
        completion = cm.UserTaskCompletion(
            exercise=exercise,
            instance=instance,
            user=user,
            points=quotient
        )
        if evaluation.get("manual", False):
            completion.state = "submitted"
        else:
            completion.state = ["incorrect", "correct"][correct]
        completion.save()
        changed = True
    else:
        if completion.state != "correct":
            if evaluation.get("manual", False):
                completion.state = "submitted"
            else:
                completion.state = ["incorrect", "correct"][correct]
                changed = True
        if correct:
            if quotient > completion.points:
                completion.points = quotient
        completion.save()


    eval_group = get_single_archived(exercise, link.revision).evaluation_group

    if changed and correct and eval_group:
        others = cm.ContentPage.objects.filter(
            evaluation_group=eval_group
        ).exclude(id=exercise.id)
        for task in others:
            link = cm.EmbeddedLink.objects.filter(
                instance=instance,
                embedded_page=task
            ).first()
            if get_single_archived(task, link.revision).evaluation_group != eval_group:
                continue
            try:
                completion = cm.UserTaskCompletion.objects.get(
                    exercise=task,
                    instance=instance,
                    user=user
                )
            except cm.UserTaskCompletion.DoesNotExist:
                completion = cm.UserTaskCompletion(
                    exercise=task,
                    instance=instance,
                    user=user
                )
                completion.state = "credited"
                completion.save()
            else:
                if completion.state not in ["correct", "credited"]:
                    completion.state = "credited"
                    completion.save()
                    
    return completion.state

