from django.urls import reverse
from reversion.models import Version

def check_user_completion(user, task_links, instance, include_links=True):
    results = []
    course = instance.course
    for link in task_links:
        exercise_obj = link.embedded_page.get_type_object()
        if link.revision is not None:
            exercise_obj = Version.objects.get_for_object(exercise_obj).get(revision=link.revision)._object_version.object

        result = exercise_obj.get_user_evaluation(user, instance)

        points = 0
        if result == "correct":
            correct = True
            points = exercise_obj.default_points
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
    for result in results:
        points_available += result["eo"].default_points
        if result["correct"]:
            points += result["eo"].default_points
        else:
            missing += 1
    
    return missing, points, points_available

def compile_student_results(user, instance, tasks_by_page):
    results_by_page = []
    total_missing = 0
    total_points = 0
    total_points_available = 0
    for page, task_links in tasks_by_page:
        page_stats = check_user_completion(user, task_links, instance)
        missing, page_points, page_points_available = get_missing_and_points(page_stats)
        total_points += page_points
        total_points_available += page_points_available
        total_missing += missing
        results_by_page.append({"page": page, "done_count": len(task_links) - missing, "task_count": len(task_links), "points": page_points, "points_available": page_points_available, "tasks_list": page_stats})
    return results_by_page, total_points, total_missing, total_points_available
