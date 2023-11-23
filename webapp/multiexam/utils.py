from collections import defaultdict
import random
import yaml
from courses import markupparser
from multiexam.models import MultipleQuestionExamAttempt

def get_used_questions(exam, instance, user):
    used_by_category = defaultdict(list)
    attempts = MultipleQuestionExamAttempt.objects.filter(
        exam=exam,
        instance=instance,
        user=user,
    )
    for attempt in attempts:
        for handle, alt_idx in attempt.questions.items():
            used_by_category[handle].append(alt_idx)

    return used_by_category


def generate_attempt_questions(exam, instance, total_questions, user=None):
    with exam.examquestionpool.fileinfo.open() as f:
        pool = yaml.safe_load(f)

    selected = {}
    categories = random.sample(pool.keys(), total_questions)
    if user is None:
        used_questions = get_used_questions(exam, instance, user)
    else:
        used_questions = {}

    for category in categories:
        alternatives = set(range(len(pool[category]["alternatives"])))
        used = used_questions.get(category, [])
        available = alternatives.difference(used) or alternatives
        selected[category] = random.choice(list(available))

    return selected


def process_questions(request, exam_script, answers):
    states = []
    parser = markupparser.MarkupParser()
    for handle, question in exam_script:
        question["question"] = "".join(
            block[1] for block in parser.parse(
                question["question"], request, None
            )
        ).strip()
        if answers.get(handle):
            question["answer"] = answers[handle]
            state = (
                answers[handle][1]
                .replace("1", "uncertain")
                .replace("2", "certain")
            )
        else:
            state = "unanswered"
        question["answer_state"] = state
        states.append(state)

    return states












