import os
import argparse
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings")

import django
django.setup()

import courses.models as c_models
import feedback.models as fb_models

def delete_exercise(args):
    name = args.name
    exercise = c_models.FileUploadExercise.objects.get(name=name)
    [fb_models.ContentFeedbackQuestion.objects.get(question=question.question).delete() for question in exercise.feedback_questions.all()]
    exercise.delete()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", dest="name", help="The name of the exercise", type=str, required=True)
    args = parser.parse_args()
    delete_exercise(args)
