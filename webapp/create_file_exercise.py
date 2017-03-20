import os
import random
import argparse
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings")

import django
django.setup()

from django.contrib.auth.models import User, Group
from django.core.files import File
from django.db import transaction
from reversion import revisions as reversion

import courses.models as c_models
import feedback.models as fb_models

DEFAULT_OBJ_COUNT = 6

def create_exercise(args):
    name = args.name
    randomize_tests = args.randomize_tests
    content = args.content
    question = args.question
    def_points = args.def_points
    man_evaluated = args.manually_evaluated
    ask_collab = args.ask_collab
    hint_count = args.hint_count
    test_count = args.test_count
    file_count = args.file_count
    stage_count = args.stage_count
    command_count = args.command_count
    tag_count = args.tag_count
    star_fb_count = args.star_fb_count
    thumb_fb_count = args.thumb_fb_count
    mc_fb_count = args.mc_fb_count
    tf_fb_count = args.tf_fb_count
    if args.count_all is not None:
        count_all = args.count_all
        hint_count = count_all
        test_count = count_all
        file_count = count_all
        stage_count = count_all
        command_count = count_all
        tag_count = count_all
        star_fb_count = count_all
        thumb_fb_count = count_all
        mc_fb_count = count_all
        tf_fb_count = count_all
        
    tags = ["tag{}".format(i) for i in range(tag_count)]
    
    feedbacks = []
    for i in range(star_fb_count):
        star_fb = fb_models.StarFeedbackQuestion(
            question_en="Star feedback question number {}".format(i),
            question_fi="Tähtipalautekysymys numero {}".format(i),
            slug=""
        )
        star_fb.save()
        feedbacks.append(star_fb)
    for i in range(thumb_fb_count):
        thumb_fb = fb_models.ThumbFeedbackQuestion(
            question_en="Thumb feedback question number {}".format(i),
            question_fi="Peukalopalautekysymys numero {}".format(i),
            slug=""
        )
        thumb_fb.save()
        feedbacks.append(thumb_fb)
    for i in range(mc_fb_count):
        mc_fb = fb_models.MultipleChoiceFeedbackQuestion(
            question_en="Multiple choice feedback question number {}".format(i),
            question_fi="Monivalintapalautekysymys numero {}".format(i),
            slug=""
        )
        mc_fb.save()
        feedbacks.append(mc_fb)
        for j in range(5): # TODO: Use a variable/constant
            mc_fb_choice = fb_models.MultipleChoiceFeedbackAnswer(
                question=mc_fb,
                answer_en="Multiplce choice feedback answer {} for question {}".format(j, i),
                answer_fi="Monivalintapalautevastaus {} kysymykselle {}".format(j, i),
            )
            mc_fb_choice.save()
    for i in range(tf_fb_count):
        tf_fb = fb_models.TextfieldFeedbackQuestion(
            question_en="Textfield feedback question number {}".format(i),
            question_fi="Tekstikenttäpalautekysymys numero {}".format(i),
            slug=""
        )
        tf_fb.save()
        feedbacks.append(tf_fb)
    cfqs = [fb_models.ContentFeedbackQuestion.objects.get(question=fb.question) for fb in feedbacks]

    main_responsible = User.objects.first()
    staff_group = Group()
    staff_group.save()
    staff_group.user_set.add(main_responsible)
    staff_group.save()

    course = c_models.Course(
        name_en="An example course",
        name_fi="Esimerkkikurssi",
        code="1234567890",
        credits=10,
        description_en="A thorough description of this course.",
        description_fi="Täyteläinen kuvaelma kurssituksesta.",
        staff_group=staff_group,
        main_responsible=main_responsible,
    )
    course.save()

    instance = c_models.CourseInstance(
        name_en="A running instance of the example course",
        name_fi="Juokseva ilmentymä esimerkkikurssista",
        course=course,
    )
    instance.save()

    instance2 = c_models.CourseInstance(
        name_en="Ye olde instance",
        name_fi="Wanhassa wara barembi",
        course=course,
    )
    instance2.save()

    course2 = c_models.Course(
        name_en="An unused course",
        name_fi="Käyttämätön kurssi",
        code="1000000X",
        credits=2.5,
        description_en="A course that doesn't actually exist and, therefore, you cannot take.",
        description_fi="Kurssi jota ei oikeasti ole olemassa, ja jota et voi siksi käydä.",
        staff_group=staff_group,
        main_responsible=main_responsible,
    )
    course2.save()

    instance_course2 = c_models.CourseInstance(
        name_en="The only instance",
        name_fi="Ainut ilmentymä",
        course=course2,
    )
    instance_course2.save()

    # TODO: Clean up to use the args

    name_en = "Example file upload exercise"
    name_fi = "Esimerkillinen tiedostotehtävä"
    content_en = "= " + name_en + " =\n\nPage contents go here."
    content_fi = "= " + name_fi + " =\n\nSivun sisältö kuuluu tänne."
    question_en = "What is the answer to this question?"
    question_fi = "Mikä on tämän kysymyksen vastaus?"
    allowed_filenames = ['*.py', 'the_name_of_this_exercise.py', 'kitten.jpg']
    
    exercise = c_models.FileUploadExercise(
        name_en=name_en, slug="", content_en=content_en, question_en=question_en,
        name_fi=name_fi,          content_fi=content_fi, question_fi=question_fi,
        default_points=def_points, manually_evaluated=man_evaluated, ask_collaborators=ask_collab,
        tags=tags, allowed_filenames=allowed_filenames,
    )
    exercise.save()
    exercise.feedback_questions.add(*cfqs)

    
    # A page that has the file upload exercise embedded

    lecture = c_models.Lecture(
        name_en="Lecture page with embedded file upload exercise",
        name_fi="Luentosivu, jolla on sisällytettynä tiedostotehtävä",
        content_en="= Lecture =\n\nSome text here.\n\n<!page=" + exercise.slug + ">\n",
        content_fi="= Luento =\n\nTekstiä tässä.\n\n<!page=" + exercise.slug + ">\n",
        default_points=1
    )
    lecture.save()

    # The links

    link = c_models.ContentGraph(
        content=exercise,
        ordinal_number=1,
    )
    link.save()

    lecture_link = c_models.ContentGraph(
        content=lecture,
        ordinal_number=2,
    )
    lecture_link.save()
    
    instance.contents.add(link)
    instance.contents.add(lecture_link)
    instance.save()
    
    for i in range(hint_count):
        hint = c_models.Hint(
            exercise=exercise,
            hint_en="Here's hint number {}".format(i),
            hint_fi="Tässäpä vihje numero {}".format(i),
        )
        hint.save()

    for i in range(4):
        file_settings = c_models.IncludeFileSettings(
            name_en="actual-instancefile{}".format(i),
            name_fi="varsinainen-instanssitiedosto{}".format(i),
            purpose=random.choice(('REFERENCE', 'INPUT', 'WRAPPER', 'TEST')),
            chown_settings=random.choice(('OWNED', 'NOT_OWNED')),
            chgrp_settings=random.choice(('OWNED', 'NOT_OWNED')),
            chmod_settings="".join(
                "rwx"[k % 3] if bool(random.getrandbits(1)) == True else "-"
                for k in range(9)
            ),
        )
        file_settings.save()
        with open('../test_files/uploadable_files/hello_world_sophisticated.py', 'r') as f:
            f_obj = File(f)
            inc_file = c_models.InstanceIncludeFile(
                instance=instance,
                default_name_en="default-instancefile{}".format(i),
                default_name_fi="oletus-instanssitiedosto{}".format(i),
                description_en="Some file that is used in all or some of the exercises in this instance.",
                description_fi="Joku tiedosto, jota käytetään kaikissa tai joissain tämän instanssin harjoituksissa.",
                fileinfo_en=f_obj,
                fileinfo_fi=f_obj,
            )
            inc_file.save()
            f2elink = c_models.InstanceIncludeFileToExerciseLink(
                include_file=inc_file,
                exercise=exercise,
                file_settings=file_settings,
            )
            f2elink.save()
            inc_file.save()
        
    for i in range(test_count):
        test = c_models.FileExerciseTest(exercise=exercise, name="test{}".format(i))
        test.save()
        if randomize_tests:
            file_range = range(random.randrange(file_count + 1))
        else:
            file_range = range(file_count)
        inc_files = []
        for j in file_range:
            file_settings = c_models.IncludeFileSettings(
                name_en="actual-test{}file{}".format(i, j),
                name_fi="varsinainen-testi{}tiedosto{}".format(i, j),
                purpose=random.choice(('REFERENCE', 'INPUT', 'WRAPPER', 'TEST')),
                chown_settings=random.choice(('OWNED', 'NOT_OWNED')),
                chgrp_settings=random.choice(('OWNED', 'NOT_OWNED')),
                chmod_settings="".join(
                    "rwx"[k % 3] if bool(random.getrandbits(1)) == True else "-"
                    for k in range(9)
                ),
            )
            file_settings.save()
            with open('../test_files/test1.txt', 'r') as f:
                f_obj = File(f)
                inc_file = c_models.FileExerciseTestIncludeFile(
                    default_name_en="default-test{}file{}".format(i, j),
                    default_name_fi="oletus-testi{}tiedosto{}".format(i, j),
                    description_en="A file used in this exercise.",
                    description_fi="Tässä tehtävässä käytetty tiedosto.",
                    exercise=exercise,
                    fileinfo_en=f_obj,
                    fileinfo_fi=f_obj,
                    file_settings=file_settings,
                )
                inc_file.save()
                inc_files.append(inc_file)
        test.required_files.add(*inc_files)
            
        if randomize_tests:
            stage_range = range(random.randrange(stage_count + 1))
        else:
            stage_range = range(stage_count)
        for j in stage_range:
            stage = c_models.FileExerciseTestStage(
                test=test,
                name_en="test{}stage{}".format(i, j),
                name_fi="testi{}vaihe{}".format(i, j),
                ordinal_number=j + 1
            )
            stage.save()
            if randomize_tests:
                cmd_range = range(random.randrange(command_count + 1))
            else:
                cmd_range = range(command_count)
            for k in cmd_range:
                cmd = c_models.FileExerciseTestCommand(
                    stage=stage,
                    command_line_en="python3 testscript.py english {} {} {}".format(i, j, k),
                    command_line_fi="python3 testiskripta.py finnish {} {} {}".format(i, j, k),
                    ordinal_number=k + 1,
                    input_text_en="text\nthat\ngoes\nline\nby\nline\n{}\n".format((k + 1) * 100),
                    input_text_fi="tekstiä\njoka\nsyötetään\nrivi\riviltä\n{}\n".format((k + 1) * 100),
                )
                cmd.save()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("name", metavar="name", help="The name of the exercise", type=str)
    parser.add_argument("--randomized-tests", dest="randomize_tests", action="store_true", help="The number of files, stages and commands in tests are randomized", default=True)
    parser.add_argument("--no-randomized-tests", dest="randomize_tests", action="store_false", help="The number of stages and commands in tests are not randomized")
    parser.add_argument("--content", dest="content", help="The contents of the exercise", type=str, default="Some content here...")
    parser.add_argument("--question", dest="question", help="The question of the exercise", type=str, default="Some question here...")
    parser.add_argument("--default-points", dest="def_points", help="Default points received from the exercise", type=int, default=1)
    parser.add_argument("--manually-evaluated", dest="manually_evaluated", action="store_true", help="Determines if the exercise is manually evaluated", default=False)
    parser.add_argument("--ask-collab", dest="ask_collab", action="store_true", help="Determines if collaborators are asked", default=False)
    parser.add_argument("--tags", dest="tag_count", help="Number of tags the exercise includes", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--hints", dest="hint_count", help="Number of hints the exercise includes", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--tests", dest="test_count", help="Number of tests the exercise includes", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--files", dest="file_count", help="Number of files each exercise test requires", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--stages", dest="stage_count", help="Number of stages each exercise test includes", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--commands", dest="command_count", help="Number of commands each test stage includes", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--star-feedback", dest="star_fb_count", help="Number of star feedback questions included to the exercise", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--thumb-feedback", dest="thumb_fb_count", help="Number of thumb feedback questions included to the exercise", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--multichoice-feedback", dest="mc_fb_count", help="Number of multiple choice feedback questions included to the exercise", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--textfield-feedback", dest="tf_fb_count", help="Number of textfield feedback questions included to the exercise", type=int, default=DEFAULT_OBJ_COUNT)
    parser.add_argument("--count-all", dest="count_all", help="Creates a certain number of each object that the exercise contains", type=int, default=None)
    args = parser.parse_args()

    with transaction.atomic(), reversion.create_revision():
        create_exercise(args)
