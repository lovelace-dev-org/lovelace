import base64
import json
import logging
from django.template import loader
from django.urls import reverse
from courses import markupparser
from utils.archive import get_single_archived, get_archived_instances
from utils.files import get_file_contents_b64
import courses.models as cm

INCORRECT = 0
CORRECT = 1
INFO = 2
ERROR = 3
DEBUG = 4
LINT_C = 10  # 10
LINT_R = 11  # 11
LINT_W = 12  # 12
LINT_E = 13  # 13

logger = logging.getLogger(__name__)

# NOTE: the amount of reverts caused by this is disgusting.
def file_upload_payload(exercise, student_files, instance, revision=None):
    payload = {"resources": {"files_to_check": {}, "checker_files": {}}, "tests": []}
    if revision is not None:
        archived = get_archived_instances(exercise, revision)
        exercise = archived["self"]
        tests = archived["fileexercisetest_set"]
        instance_file_links = archived["instanceincludefiletoexerciselink_set"]
        # MONKEY PATCH FOR BROKEN ARCHIVED EXERCISES
        if not instance_file_links:
            instance_file_links = exercise.instanceincludefiletoexerciselink_set.get_queryset()
    else:
        tests = exercise.fileexercisetest_set.get_queryset()
        instance_file_links = exercise.instanceincludefiletoexerciselink_set.get_queryset()

    # Resources
    for a_file in student_files:
        a_file.seek(0)
        payload["resources"]["files_to_check"][a_file.name] = base64.b64encode(
            a_file.read()
        ).decode("utf-8")

    all_required_exercise = set()
    all_required_instance = set()

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
            all_required_exercise.add(req_file)
            test_payload["required_files"].append(f"ex-{req_file.id}")
        for req_file in required_instance_files:
            all_required_instance.add(req_file.id)
            test_payload["required_files"].append(f"in-{req_file.id}")

        for stage in stages:
            if revision is not None:
                archived = get_archived_instances(stage, revision)
                stage = archived["self"]
                commands = archived["fileexercisetestcommand_set"]
            else:
                commands = stage.fileexercisetestcommand_set.all()

            command_list = []
            for command in commands:
                command_list.append(
                    {
                        "input_text": command.input_text,
                        "return_value": command.return_value,
                        "cmd": command.command_line,
                        "ordinal": command.ordinal_number,
                        "timeout": command.timeout.total_seconds(),
                        "json_output": command.json_output,
                        "stdout": command.significant_stdout,
                        "stderr": command.significant_stderr,
                    }
                )

            test_payload["stages"].append(
                {
                    "id": stage.id,
                    "ordinal": stage.ordinal_number,
                    "name": stage.name,
                    "commands": command_list,
                }
            )

        payload["tests"].append(test_payload)

    for ex_file in all_required_exercise:
        payload["resources"]["checker_files"][f"ex-{ex_file.id}"] = {
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

        if i_file.id in all_required_instance:
            payload["resources"]["checker_files"][f"in-{i_file.id}"] = {
                "content": get_file_contents_b64(i_file),
                "purpose": if_link.file_settings.purpose,
                "name": if_link.file_settings.name,
                "chmod": if_link.file_settings.chmod_settings,
            }

    logger.debug(json.dumps(payload, indent=4))
    return payload


def compile_evaluation_data(request, evaluation_tree, evaluation_obj, context=None):
    log = evaluation_tree["test_tree"].get("log", [])

    # render all individual messages in the log tree
    parser = markupparser.MarkupParser()
    for test in log:
        test["title"] = "".join(
            block[1] for block in parser.parse(test["title"], request, context)
        ).strip()
        test["runs"].sort(key=lambda run: run["correct"])
        for run in test["runs"]:
            for output in run["output"]:
                output["msg"] = "".join(
                    block[1] for block in parser.parse(output["msg"], request, context)
                ).strip()

    debug_json = json.dumps(evaluation_tree, indent=4)

    hints = [
        "".join(
            block[1] for block in parser.parse(msg, request, context)
        ).strip()
        for msg in evaluation_tree["test_tree"].get("hints", [])
    ]
    triggers = evaluation_tree["test_tree"].get("triggers", [])

    t_file = loader.get_template("courses/file-exercise-evaluation.html")
    c_file = {
        "debug_json": debug_json,
        "evaluation_tree": evaluation_tree["test_tree"],
    }
    t_exercise = loader.get_template("courses/exercise-evaluation.html")
    c_exercise = {
        "evaluation": evaluation_obj.correct,
        "manual": context["content_page"].manually_evaluated,
        "answer_url": context.get("answer_url", ""),
        "points": evaluation_tree["points"],
        "max": evaluation_tree["max"],
    }
    t_messages = loader.get_template("courses/exercise-evaluation-messages.html")

    data = {
        "file_tabs": t_file.render(c_file, request),
        "result": t_exercise.render(c_exercise),
        "evaluation": evaluation_obj.correct,
        "points": evaluation_obj.points,
        "messages": t_messages.render({"log": log}),
        "hints": hints,
        "triggers": triggers,
    }

    return data


def render_json_feedback(log, request, course, instance, content, answer_id=None):
    """
    Renders exercise feedback from the exercise log JSON format. Parses
    messages, hints, triggers, and the final result from the log and returns
    them as a dictionary.

    Messages and hints are ran through the markupparser, which makes it
    possible to include any markup in the log.
    """

    # render all individual messages in the log tree
    triggers = []
    hints = []

    context = {"course_slug": course.slug, "instance_slug": instance.slug}

    parser = markupparser.MarkupParser()
    for test in log["tests"]:
        test["title"] = "".join(
            block[1] for block in parser.parse(test["title"], request, context)
        ).strip()
        for run in test["runs"]:
            run["correct"] = True
            for output in run["output"]:
                output["msg"] = "".join(
                    block[1] for block in parser.parse(output["msg"], request, context)
                ).strip()
                triggers.extend(output.get("triggers", []))
                hints.extend(
                    "".join(
                        block[1] for block in parser.parse(msg, request, context)
                    ).strip()
                    for msg in output.get("hints", [])
                )
                if output["flag"] in (INCORRECT, ERROR):
                    run["correct"] = False

        test["runs"].sort(key=lambda run: run["correct"])

    answer_url = (
        reverse(
            "courses:show_answers",
            kwargs={
                "user": request.user,
                "course": course,
                "instance": instance,
                "exercise": content,
            },
        )
        + "#"
        + str(answer_id)
    )

    t_messages = loader.get_template("courses/exercise-evaluation-messages.html")
    t_exercise = loader.get_template("courses/exercise-evaluation.html")
    c_exercise = {
        "evaluation": log["result"]["correct"],
        "manual": content.manually_evaluated,
        "answer_url": request.build_absolute_uri(answer_url),
        "points": log["result"]["score"],
        "max": log["result"]["max"],
    }
    feedback = {
        "messages": t_messages.render({"log": log["tests"]}),
        "hints": hints,
        "triggers": triggers,
        "result": t_exercise.render(c_exercise),
    }
    return feedback


def apply_late_rule(exercise, evaluation, rule, days_late):
    quotient = evaluation.get("points", 0) / evaluation.get("max", exercise.default_points)
    return eval(
        rule.format(
            p=evaluation.get("points", 0),
            m=evaluation.get("max", exercise.default_points),
            q=quotient,
            d=days_late,
        )
    )

def is_late(graph, user, answer_date):
    exemption = cm.DeadlineExemption.objects.filter(user=user, contentgraph=graph).first()
    if exemption:
        deadline = exemption.new_deadline
    else:
        deadline = graph.deadline

    return deadline and (answer_date > deadline)


def update_completion(exercise, instance, user, evaluation, answer_date, overwrite=False):
    link = cm.EmbeddedLink.objects.filter(instance=instance, embedded_page=exercise).first()
    parent_graph = link.parent.contentgraph_set.get_queryset().get(instance=instance)
    late = is_late(parent_graph, user, answer_date)

    changed = False
    correct = evaluation["evaluation"]
    if correct:
        if late and parent_graph.late_rule:
            days_late = (answer_date - parent_graph.deadline).days + 1
            quotient = apply_late_rule(exercise, evaluation, parent_graph.late_rule, days_late)
        else:
            try:
                quotient = evaluation.get("points", 0) / evaluation.get(
                    "max", exercise.default_points
                )
            except ZeroDivisionError:
                quotient = 0
    else:
        quotient = 0

    if quotient > 1:
        raise ValueError("Quotient cannot be higher than 1")

    try:
        completion = cm.UserTaskCompletion.objects.get(
            exercise=exercise, instance=instance, user=user
        )
    except cm.UserTaskCompletion.DoesNotExist:
        completion = cm.UserTaskCompletion(
            exercise=exercise, instance=instance, user=user, points=quotient
        )
        if evaluation.get("manual", False):
            completion.state = "submitted"
        else:
            completion.state = ["incorrect", "correct"][correct]
        completion.save()
        changed = True
    else:
        if completion.state != "correct" or overwrite:
            if evaluation.get("manual", False):
                completion.state = "submitted"
            else:
                completion.state = ["incorrect", "correct"][correct]
                changed = True
        if correct:
            if quotient > completion.points or overwrite:
                completion.points = quotient
        completion.save()

    eval_group = get_single_archived(exercise, link.revision).evaluation_group

    if changed and correct and eval_group:
        others = cm.ContentPage.objects.filter(evaluation_group=eval_group).exclude(id=exercise.id)
        for task in others:
            link = cm.EmbeddedLink.objects.filter(instance=instance, embedded_page=task).first()
            if link is None:
                continue
            if get_single_archived(task, link.revision).evaluation_group != eval_group:
                continue
            try:
                completion = cm.UserTaskCompletion.objects.get(
                    exercise=task, instance=instance, user=user
                )
            except cm.UserTaskCompletion.DoesNotExist:
                completion = cm.UserTaskCompletion(exercise=task, instance=instance, user=user)
                completion.state = "credited"
                completion.save()
            else:
                if completion.state not in ["correct", "credited"]:
                    completion.state = "credited"
                    completion.save()

    return completion.state


def best_result(user, instance, group_tag):
    grouped_tasks = cm.ContentPage.objects.filter(evaluation_group=group_tag)
    best_score = -1
    best_task = grouped_tasks[0]
    for task in grouped_tasks:
        correct, score = task.get_user_evaluation(user, instance)
        if correct == "correct":
            if score > best_score:
                best_score = score
                best_task = task
    return best_score, best_task
