import os
import argparse
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings")

import django
django.setup()

import courses.models as c_models
import feedback.models as fb_models

def create_exercise(args):
    name = args.name
    content = args.content
    question = args.question
    def_points = args.def_points
    man_evaluated = args.manually_evaluated
    ask_collab = args.ask_collab
    hint_count = args.hint_count
    test_count = args.test_count
    stage_count = args.stage_count
    command_count = args.command_count
    tag_count = args.tag_count
    star_fb_count = args.star_fb_count
    thumb_fb_count = args.thumb_fb_count
    mc_fb_count = args.mc_fb_count
    tf_fb_count = args.tf_fb_count

    tags = ["tag{}".format(i) for i in range(tag_count)]

    
    feedbacks = []
    for i in range(star_fb_count):
        star_fb = fb_models.StarFeedbackQuestion(question="Star feedback question number {}".format(i), slug="")
        star_fb.save()
        feedbacks.append(star_fb)
    for i in range(thumb_fb_count):
        thumb_fb = fb_models.ThumbFeedbackQuestion(question="Thumb feedback question number {}".format(i), slug="")
        thumb_fb.save()
        feedbacks.append(thumb_fb)
    for i in range(mc_fb_count):
        mc_fb = fb_models.MultipleChoiceFeedbackQuestion(question="Multiple choice feedback question number {}".format(i), slug="")
        mc_fb.save()
        feedbacks.append(mc_fb)
    for i in range(tf_fb_count):
        tf_fb = fb_models.TextfieldFeedbackQuestion(question="Textfield feedback question number {}".format(i), slug="")
        tf_fb.save()
        feedbacks.append(tf_fb)
    cfqs = [fb_models.ContentFeedbackQuestion.objects.get(question=fb.question) for fb in feedbacks]
    
    exercise = c_models.FileUploadExercise(name=name, slug="", content=content, question=question, default_points=def_points,
                                           manually_evaluated=man_evaluated, ask_collaborators=ask_collab, tags=tags)
    exercise.save()
    exercise.feedback_questions.add(*cfqs)
    
    for i in range(hint_count):
        hint = c_models.Hint(exercise=exercise, hint="Here's hint number {}".format(i))
        hint.save()
        
    for i in range(test_count):
        test = c_models.FileExerciseTest(exercise=exercise, name="test{}".format(i))
        test.save()
        for j in range(stage_count):
            stage = c_models.FileExerciseTestStage(test=test, name="test{}stage{}".format(i, j),  ordinal_number=j + 1)
            stage.save()
            for k in range(command_count):
                cmd = c_models.FileExerciseTestCommand(stage=stage, command_line="python testiskripta.py {} {} {}".format(i, j, k), ordinal_number=k + 1)
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
    parser.add_argument("--hints", dest="hint_count", help="Number of hints the exercise includes", type=int, default=5)
    parser.add_argument("--tests", dest="test_count", help="Number of tests the exercise includes", type=int, default=5)
    parser.add_argument("--stages", dest="stage_count", help="Number of stages each exercise test includes", type=int, default=5)
    parser.add_argument("--commands", dest="command_count", help="Number of commands each test stage includes", type=int, default=5)
    parser.add_argument("--star-feedback", dest="star_fb_count", help="Number of star feedback questions included to the exercise", type=int, default=5)
    parser.add_argument("--thumb-feedback", dest="thumb_fb_count", help="Number of thumb feedback questions included to the exercise", type=int, default=5)
    parser.add_argument("--multichoice-feedback", dest="mc_fb_count", help="Number of multiple choice feedback questions included to the exercise", type=int, default=5)
    parser.add_argument("--textfield-feedback", dest="tf_fb_count", help="Number of textfield feedback questions included to the exercise", type=int, default=5)
    args = parser.parse_args()
    create_exercise(args)
