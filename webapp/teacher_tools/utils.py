from django.http import QueryDict
from django.urls import reverse
import courses.models as cm


def check_user_completion(user, tasks, instance, completion_qs, include_links=True):
    results = []
    course = instance.course
    for link in tasks:
        exercise_obj = link.embedded_page
        try:
            completion = completion_qs.get(
                exercise=exercise_obj,
            )
            result = completion.state
        except cm.UserTaskCompletion.DoesNotExist:
            result = "unanswered"

        points = 0
        if result == "correct":
            correct = True
            points = completion.points * exercise_obj.default_points
        elif result == "credited":
            correct = True
        else:
            correct = False

        result_dict = {"eo": exercise_obj, "correct": correct, "points": points, "result": result}
        if include_links:
            result_dict["answers_link"] = reverse(
                "courses:show_answers",
                kwargs={
                    "user": user,
                    "course": course,
                    "instance": instance,
                    "exercise": exercise_obj,
                },
            )
        results.append(result_dict)

    return results


def get_missing_and_points(results):
    missing = 0
    points = 0
    points_available = 0
    tasks = 0
    groups_counted = []
    group_scores = {}
    for result in results:
        if result["eo"].evaluation_group:
            evalgroup = result["eo"].evaluation_group
            if evalgroup not in groups_counted:
                points_available += result["eo"].default_points
                groups_counted.append(evalgroup)
                tasks += 1
                if not result["correct"]:
                    missing += 1
            group_scores[evalgroup] = max(result["points"], group_scores.get(evalgroup, 0))
        else:
            points_available += result["eo"].default_points
            tasks += 1
            if result["correct"]:
                points += result["points"]
            else:
                missing += 1


    for group in groups_counted:
        points += group_scores[group]

    return tasks, missing, points, points_available


def compile_student_results(user, instance, tasks_by_page, summary=False):
    results_by_page = []
    total_missing = 0
    total_points = 0
    total_points_available = 0
    completion_qs = cm.UserTaskCompletion.objects.filter(user=user, instance=instance)

    grouped_page_scores = {}
    grouped_page_max = {}
    grouped_missing = {}

    for context, task_links in tasks_by_page:
        page = context.content
        page_stats = check_user_completion(user, task_links, instance, completion_qs)
        tasks, missing, page_points, page_points_available = get_missing_and_points(page_stats)
        if context.scoring_group:
            grouped_page_scores[context.scoring_group] = max(
                grouped_page_scores.get(context.scoring_group, 0),
                page_points * context.score_weight,
            )
            grouped_page_max[context.scoring_group] = max(
                grouped_page_max.get(context.scoring_group, 0),
                page_points_available * context.score_weight,
            )
            grouped_missing[context.scoring_group] = min(
                grouped_missing.get(context.scoring_group, 9999), missing
            )
        else:
            total_points += page_points * context.score_weight
            total_points_available += page_points_available * context.score_weight
            total_missing += missing
        page_results = {
            "page": page.name,
            "done_count": tasks - missing,
            "task_count": tasks,
            "points": page_points,
            "points_available": page_points_available,
            "score": page_points * context.score_weight,
        }
        if not summary:
            page_results["page"] = page
            page_results["tasks_list"] = page_stats
        results_by_page.append(page_results)

    for group, max_score in grouped_page_max.items():
        total_points_available += max_score
        total_points += grouped_page_scores[group]
        total_missing += grouped_missing[group]

    return results_by_page, total_points, total_missing, total_points_available


# NOTE: this REALLY should not be needed
def reconstruct_answer_form(task_type, answer):
    if task_type == "TEXTFIELD_EXERCISE":
        return {"answer": answer.given_answer}
    if task_type == "MULTIPLE_CHOICE_EXERCISE":
        return {"-radio": answer.chosen_answer_id}
    if task_type == "CHECKBOX_EXERCISE":
        return dict((str(a.id), a.id) for a in answer.chosen_answers.all())
    if task_type == "MULTIPLE_QUESTION_EXAM":
        answer_form = QueryDict(mutable=True)
        answer_form.update({
            "attempt_id": answer.attempt.id
        })
        for key, (choices, certainty) in answer.answers.items():
            answer_form.setlist(key, choices)
        return answer_form

    raise ValueError("Unsupported task type")
