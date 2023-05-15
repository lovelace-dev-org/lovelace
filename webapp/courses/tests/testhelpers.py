import os
from django.core import files
from django.conf import settings
import courses.models as cm


class TestUrls:
    course_url = "/testcourse/testinstance/"
    plain_page_url = "/testcourse/testinstance/plain-lecture-page/"
    media_page_url = "/testcourse/testinstance/media-lecture-page/"
    checkbox_page_url = "/testcourse/testinstance/checkbox-exercise-page/"
    multiple_choice_page_url = "/testcourse/testinstance/multiple-choice-exercise-page/"
    textfield_page_url = "/testcourse/testinstance/textfield-exercise-page/"
    file_upload_page_url = "/testcourse/testinstance/file-upload-exercise-page/"
    template_page_url = "/testcourse/testinstance/template-exercise-page/"
    plain_term_page_url = "/testcourse/testinstance/plain-term-page/"
    tab_term_page_url = "/testcourse/testinstance/tab-term-page/"
    link_term_page_url = "/testcourse/testinstance/link-term-page/"


PLAIN_CONTENT = """
= Heading 1 =

There is some text here

== Heading 2 ==

Some ''more'' text here

=== Heading 3 ===

'''Even more''' text here

==== Heading 4 ====

There's also a [[https://docs.python.org/3/|link to Python 3 documentation]]

===== Heading 5 =====

And a [!hint=sample-highlight!]triggerable highlight[!hint!]
"""

MEDIA_CONTENT = """
<!file=testfile-txt>
<!file=testfile-txt|link_only=True>
<!image=testimage|caption=test>
<!image=testimage|alt=test>
"""


class TestSettingsNotUsed(Exception):
    pass


def create_admin_user():
    testuser_admin = cm.User(username="testadmin", is_staff=True, is_superuser=True, is_active=True)
    testuser_admin.save()
    return testuser_admin


def create_text_file():
    testfile_file_object = files.base.ContentFile("aasisvengaa", "testfile.txt")
    testfile = cm.File(name="testfile-txt", typeinfo="text file", fileinfo=testfile_file_object)
    testfile.save()
    return testfile


def create_image():
    testimage_file_object = files.images.ImageFile(
        open(os.path.join(settings.STATIC_ROOT, "courses", "correct-96.png"), "rb"),
        "testimage.png",
    )
    testimage = cm.Image(name="testimage", description="test image", fileinfo=testimage_file_object)
    testimage.save()
    return testimage


def create_frontpage():
    page = cm.Lecture(name="front page", content="this is a front page")
    page.save()
    return page


def create_plain_page():
    page = cm.Lecture(name="plain lecture page", content=PLAIN_CONTENT)
    page.save()
    return page


def create_media_page():
    create_text_file()
    create_image()

    page = cm.Lecture(name="media lecture page", content=MEDIA_CONTENT)
    page.save()
    return page


def create_course_with_instance():
    testcourse = cm.Course(name="testcourse")
    testcourse.save()

    testinstance = cm.CourseInstance(name="testinstance", course=testcourse)
    testinstance.save()
    return testcourse, testinstance


def add_content_graph(content, instance, ordinal):
    context = cm.ContentGraph(content=content, ordinal_number=ordinal, instance=instance)
    context.save()


def create_checkbox_exercise():
    exercise = cm.CheckboxExercise(name="test checkbox exercise", content="some content")
    exercise.save()
    answer_1 = cm.CheckboxExerciseAnswer(exercise=exercise, answer="correct answer", correct=True)
    answer_1.save()
    answer_2 = cm.CheckboxExerciseAnswer(
        exercise=exercise, answer="incorrect answer", correct=False
    )
    answer_2.save()
    return exercise


def create_checkbox_exercise_page():
    create_checkbox_exercise()
    page = cm.Lecture(name="checkbox exercise page", content="<!page=test-checkbox-exercise>")
    page.save()
    return page


def create_multiple_choice_exercise():
    exercise = cm.MultipleChoiceExercise(
        name="test multiple choice exercise", content="some content"
    )
    exercise.save()
    answer_1 = cm.MultipleChoiceExerciseAnswer(
        exercise=exercise, answer="correct answer", correct=True
    )
    answer_1.save()
    answer_2 = cm.MultipleChoiceExerciseAnswer(
        exercise=exercise, answer="incorrect answer", correct=False
    )
    answer_2.save()
    return exercise


def create_multiple_choice_exercise_page():
    create_multiple_choice_exercise()
    page = cm.Lecture(
        name="multiple choice exercise page",
        content="<!page=test-multiple-choice-exercise>",
    )
    page.save()
    return page


def create_textfield_exercise():
    exercise = cm.TextfieldExercise(name="test textfield exercise", content="some content")
    exercise.save()
    answer_1 = cm.TextfieldExerciseAnswer(
        exercise=exercise, answer=r"correct answer\s*", correct=True
    )
    answer_1.save()
    return exercise


def create_textfield_exercise_page():
    create_textfield_exercise()
    page = cm.Lecture(name="textfield exercise page", content="<!page=test-textfield-exercise>")
    page.save()
    return page


def create_file_upload_exercise():
    exercise = cm.FileUploadExercise(name="test file upload exercise", content="some content")
    exercise.save()
    return exercise


def create_file_upload_exercise_page():
    create_file_upload_exercise()
    page = cm.Lecture(name="file upload exercise page", content="<!page=test-file-upload-exercise>")
    page.save()
    return page


def create_template_exercise():
    exercise = cm.RepeatedTemplateExercise(name="test template exercise", content="some content")
    exercise.save()
    return exercise


def create_template_exercise_page():
    create_template_exercise()
    page = cm.Lecture(name="template exercise page", content="<!page=test-template-exercise>")
    page.save()
    return page


def create_plain_term(course):
    term = cm.Term(course=course, name="plain term", description="this is a plain term")
    term.save()
    return term


def create_term_with_tab(course):
    term = cm.Term(course=course, name="term with tab", description="this is a term with a tab")
    term.save()
    tab = cm.TermTab(term=term, title="test tab", description="tab description")
    tab.save()
    return term


def create_term_with_link(course):
    term = cm.Term(course=course, name="term with link", description="this is a term with a link")
    term.save()
    link = cm.TermLink(
        term=term, url="https://docs.python.org/3/", link_text="Python documentation"
    )
    link.save()
    return term


def create_page_with_plain_term(course):
    create_plain_term(course)
    page = cm.Lecture(name="plain term page", content="[!term=plain term!]plain term[!term!]")
    page.save()
    return page


def create_page_with_tab_term(course):
    create_term_with_tab(course)
    page = cm.Lecture(name="tab term page", content="[!term=tab term!]tab term[!term!]")
    page.save()
    return page


def create_page_with_link_term(course):
    create_term_with_link(course)
    page = cm.Lecture(name="link term page", content="[!term=link term!]link term[!term!]")
    page.save()
    return page
