from collections import defaultdict
import random
import yaml
from courses import markupparser
from multiexam.models import MultipleQuestionExamAttempt

def get_used_questions(exam, instance, user):
    """
    Get a list of questions that have been assigned to a user previously in the same course
    instance. If user is None, returns used questions for all general exams in the same instance.

    Returns a dictonary with category handles as keys, and used alternative indices in a list as
    values.
    """

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
    """
    Chooses random questions for an exam attempt.
    First selects a number of question categories equal to total_questions
    Second, for general exams, gets the list of previously used question alternatives per category
    Third, chooses a random unused (if possible) alternative for each selected category

    Returns a dictonary with category handles as keys, and chosen alternative indices in a list as
    values.
    """

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
    """
    Processes questions for being displayed in the exam interface. The process includes rendering
    each question's markup, and going through previously saved answers to set the state of each
    questions to one of 'unanswered', 'uncertain', or 'certain'.

    Rendered markup and question state are written into the exam_script data structure.
    States are returned as a list.

    Note: Needs the request paramater because it needs to be passed on to the markup parser.
    """

    states = []
    parser = markupparser.MarkupParser()
    for handle, question in exam_script:

        # block[1] is the rendered markup itself, rest is context information for editing widgets
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












