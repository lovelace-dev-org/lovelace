from django.urls import reverse
import courses.models as cm
from reversion.models import Version

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

        result_dict = {
            "eo": exercise_obj,
            "correct": correct,
            "points": points,
            "result": result
        }
        if include_links:
            result_dict["answers_link"] = reverse("courses:show_answers", kwargs={
                "user": user,
                "course": course,
                "instance": instance,
                "exercise": exercise_obj
            })
        results.append(result_dict)

    return results

def get_missing_and_points(results):
    missing = 0
    points = 0
    points_available = 0
    groups_counted = []
    group_scores = {}
    for result in results:
        if result["eo"].evaluation_group:
            evalgroup = result["eo"].evaluation_group
            if evalgroup not in groups_counted:
                points_available += result["eo"].default_points
                groups_counted.append(evalgroup)
            group_scores[evalgroup] = max(result["points"], group_scores.get(evalgroup, 0))
        else:
            points_available += result["eo"].default_points
            if result["correct"]:
                points += result["points"]
            else:
                missing += 1

    for group in groups_counted:
        points += group_scores[group]
    
    return missing, points, points_available

def compile_student_results(user, instance, tasks_by_page, summary=False):
    results_by_page = []
    total_missing = 0
    total_points = 0
    total_points_available = 0
    completion_qs = cm.UserTaskCompletion.objects.filter(
        user=user,
        instance=instance
    )
    for context, task_links in tasks_by_page:
        page = context.content
        page_stats = check_user_completion(user, task_links, instance, completion_qs)
        missing, page_points, page_points_available = get_missing_and_points(page_stats)
        total_points += page_points * context.score_weight
        total_points_available += page_points_available * context.score_weight
        total_missing += missing
        page_results = {
            "page": page.name,
            "done_count": len(task_links) - missing,
            "task_count": len(task_links),
            "points": page_points,
            "points_available": page_points_available,
            "score": page_points * context.score_weight,
        }
        if not summary:
            page_results["page"] = page
            page_results["tasks_list"] = page_stats
        results_by_page.append(page_results)
    return results_by_page, total_points, total_missing, total_points_available
