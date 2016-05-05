import os
import argparse
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings")

import django
django.setup()

import courses.models as models

def create_exercise(args):
    name = args.name
    content = args.content
    question = args.question
    def_points = args.def_points
    man_evaluated = args.manually_evaluated
    ask_collab = args.ask_collab
    test_count = args.test_count
    stage_count = args.stage_count
    command_count = args.command_count
    tag_count = args.tag_count

    tags = ["tag{}".format(i) for i in range(tag_count)]
    exercise = models.FileUploadExercise(name=name, slug="", content=content, question=question, default_points=def_points,
                                         manually_evaluated=man_evaluated, ask_collaborators=ask_collab, tags=tags)
    exercise.save()
    for i in range(test_count):
        test = models.FileExerciseTest(exercise=exercise, name="test{}".format(i))
        test.save()
        for j in range(stage_count):
            stage = models.FileExerciseTestStage(test=test, name="test{}stage{}".format(i, j),  ordinal_number=j + 1)
            stage.save()
            for k in range(command_count):
                cmd = models.FileExerciseTestCommand(stage=stage, command_line="python testiskripta.py {} {} {}".format(i, j, k), ordinal_number=k + 1)
                cmd.save()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", dest="name", help="The name of the exercise", type=str, required=True)
    parser.add_argument("--content", dest="content", help="The contents of the exercise", type=str, default="Some content here...")
    parser.add_argument("--question", dest="question", help="The question of the exercise", type=str, default="Some question here...")
    parser.add_argument("--default-points", dest="def_points", help="Default points received from the exercise", type=int, default=1)
    parser.add_argument("--manually-evaluated", dest="manually_evaluated", action="store_true", help="Determines if the exercise is manually evaluated", default=False)
    parser.add_argument("--ask-collab", dest="ask_collab", action="store_true", help="Determines if collaborators are asked", default=False)
    parser.add_argument("--tags", dest="tag_count", help="Number of tags the exercise includes", type=int, default=5)
    parser.add_argument("--tests", dest="test_count", help="Number of tests the exercise includes", type=int, default=5)
    parser.add_argument("--stages", dest="stage_count", help="Number of stages each exercise test includes", type=int, default=5)
    parser.add_argument("--commands", dest="command_count", help="Number of commands each test stage includes", type=int, default=5)
    args = parser.parse_args()
    create_exercise(args)
