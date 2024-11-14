from collections import defaultdict
import random
import yaml
from cerberus import Validator
from courses import markupparser
from multiexam.models import MultipleQuestionExamAttempt

exam_schema = {
    'root': {
        'type': 'dict',
        'valuesrules': {
            'type': 'dict',
            'schema': {
                'alternatives': {
                    'type': 'list',
                    'required': True,
                    'schema': {
                        'type': 'dict',
                        'schema': {
                            'question': {'type': 'string', 'required': True},
                            'summary': {'type': 'string', 'required': True},
                            'type': {
                                'type': 'string',
                                'required': True,
                                'allowed': ['checkbox', 'radio']
                            },
                            'correct': {
                                'type': 'string',
                                'required': True,
                                'regex': '^[a-z]+$'

                            },
                            'options': {
                                'type': 'dict',
                                'required': True,
                                'keysrules': {'regex': '^[a-z]$'},
                                'valuesrules': {'type': 'string'}
                            }
                        }
                    }
                },
                'value': {'type': 'integer', 'required': False, 'default':1}
            }
        }
    }
}

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
    categories = random.sample(list(pool.keys()), total_questions)
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


class ExamValidator(Validator):

    def check_possible_answers(self):
        """
        Checks if the correct answers specified in the document are valid.

        This method iterates through each question type and its corresponding
        alternatives in the document. For each alternative, it verifies that
        all characters in the 'correct' answer are present in the 'options' keys.

        If it finds an invalid correct answer, it adds an error to the error list.

        Returns is_valid:
           is_valid(bool): True if all correct answers are valid, False otherwise.

        """

        is_valid = True
        for question_type, question_value in self.document["root"].items():
            alternatives = question_value["alternatives"]
            for alt in alternatives:
                option_keys = list(alt["options"].keys())
                if not all (char in option_keys for char in alt["correct"]):
                    is_valid = False
                    self._error(
                        "correct",
                        f"Question {question_type} has invalid correct answer "
                        f"'{alt['correct']}' in alternative with summary '{alt['summary']}'"
                    )
        return is_valid

def validate_exam(exam):
    """
    Validates the given exam data against a predefined schema. It also check if the correct answer is part of the available options keys.
    Args:
        exam (dict): The exam data to be validated.
    Returns a tuple (valid, errors) where:
        valid(bool): True if the exam data is valid according to the schema, False otherwise.
        errors(dict): A dictionary of validation errors if the exam data is invalid, empty otherwise.
    """
    print("Validating")

    # Initialize the validator
    v = ExamValidator(exam_schema)

    # Validate the data
    if not v.validate({"root": exam}):
        return False, v.errors
    # Only if document is well-formed, do additional checks
    if not v.check_possible_answers():
        return False, v.errors
    return True, []

def compare_exams (exams_per_lang, primary_lang):
    """
    Compare exam models in different languages to the primary one
    Args:
        exams_per_lang (dict): Dictionary of exam question pools, keys are languages
        primary_lang (str): Indicator of which one is considered primary
    Returns tuple (valid,errors):
            valid(bool) The boolean is True if the exams are considered equivalent, False otherwise.
            errors(list) The list contains error messages describing the differences between the exams.
    The function performs the following checks:
        1. Verifies that both exams have the same names for the question types.
        2. For each question type, checks that the number of alternatives is the same.
        3. For each alternative, checks that the question type is the same.
        4. For each alternative, checks that the options are the same.
        5. For each alternative, checks that the correct answers are the same.
    If any of these checks fail, the function returns False and a list of error messages describing the differences.
    """
    errors = []
    print("Comparing")

    # Check that the two exams have the same question types
    primary_exam = exams_per_lang.pop(primary_lang)
    primary_categories = set(primary_exam)

    for lang_code, exam in exams_per_lang.items():
        categories = set(exam)
        if categories != primary_categories:
            extra = categories - primary_categories
            missing = primary_categories - categories
            if extra:
                errors.append(lang_code, f"Extra keys: {extra}")
            if missing:
                errors.append(lang_code, f"Missing keys: {missing}")
            return False, errors


    for category in primary_categories:

        primary_alts = primary_exam[category]["alternatives"]

        for lang_code, exam in exams_per_lang.items():
            if len(primary_exam[category]) != len(exam[category]):
                errors.append((
                    lang_code,
                    f"Different number of alternatives for question type '{question_type}'."
                ))
                continue

            for primary_alt, alt in zip(primary_alts, exam[category]["alternatives"]):
                if primary_alt["type"] != alt["type"]:
                    errors.append((
                        lang_code,
                        f"Alternative <{alt['summary']}> of <{category}> "
                        "has different question type from primary"
                    ))
                    continue

                if set(primary_alt["options"]) != set(alt["options"]):
                    errors.append((
                        lang_code,
                        f"Alternative <{alt['summary']}> of <{category}> "
                        "has different options from primary"
                    ))
                    continue

                if primary_alt["correct"] != alt["correct"]:
                    errors.append((
                        lang_code,
                        f"Alternative <{alt['summary']}> of <{category}> "
                        "has different correct answer from primary"
                    ))
                    continue

    return not errors, errors










