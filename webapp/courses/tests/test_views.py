"""
Basic test suite that ensures all content views - including embedded content -
render without errors. Also tests that all of them can be created and linked to
course instances on the model level.

This test suite must be run with a configuration file marked with a testing
flag and that uses a different MEDIA_ROOT than development or production
settings. The test setup creates some files and deletes the entire MEDIA_ROOT
path afterwards. 
"""

import os
import shutil
from django.conf import settings
from django.test import TestCase
import courses.tests.testhelpers as helpers


class TestSettingsNotUsed(Exception):
    pass


class ViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Aborts testing if the settings file has not been explicitly marked as
        test configuration settings. This is a safeguard against accidentally
        wiping a dev or production media root empty at teardown.
        """

        if getattr(settings, "TEST_SETTINGS", False):
            super().setUpClass()
        else:
            raise TestSettingsNotUsed(
                "Using a settings file without TEST_SETTINGS set to True is not allowed."
            )

    @classmethod
    def tearDownClass(cls):
        """
        Remove the media root directory defined in the unit test settings file.
        Needed to clean up files written to disk when creating media models for
        tests.
        """

        super().tearDownClass()
        if getattr(settings, "TEST_SETTINGS", False):
            shutil.rmtree(settings.MEDIA_ROOT)
            os.rmdir(os.path.dirname(settings.MEDIA_ROOT))

    @classmethod
    def setUpTestData(cls):
        """
        Sets up a test course with one instance and several pages.
        """

        helpers.create_admin_user()
        test_frontpage = helpers.create_frontpage()
        test_page_plain = helpers.create_plain_page()
        test_page_media = helpers.create_media_page()
        test_page_checkbox = helpers.create_checkbox_exercise_page()
        test_page_multiple_choice = helpers.create_multiple_choice_exercise_page()
        test_page_textfield = helpers.create_textfield_exercise_page()
        test_page_file_upload = helpers.create_file_upload_exercise_page()
        test_page_template = helpers.create_template_exercise_page()
        test_course, test_instance = helpers.create_course_with_instance()
        test_page_plain_term = helpers.create_page_with_plain_term(test_course)
        test_page_tab_term = helpers.create_page_with_tab_term(test_course)
        test_page_link_term = helpers.create_page_with_link_term(test_course)
        helpers.add_content_graph(test_frontpage, test_instance, 0)
        helpers.add_content_graph(test_page_plain, test_instance, 1)
        helpers.add_content_graph(test_page_media, test_instance, 2)
        helpers.add_content_graph(test_page_checkbox, test_instance, 3)
        helpers.add_content_graph(test_page_multiple_choice, test_instance, 4)
        helpers.add_content_graph(test_page_textfield, test_instance, 5)
        helpers.add_content_graph(test_page_file_upload, test_instance, 6)
        helpers.add_content_graph(test_page_template, test_instance, 7)
        helpers.add_content_graph(test_page_plain_term, test_instance, 8)
        helpers.add_content_graph(test_page_tab_term, test_instance, 9)
        helpers.add_content_graph(test_page_link_term, test_instance, 10)
        test_instance.frontpage = test_frontpage
        test_instance.save()

    def test_index_page_view(self):
        """
        Tests that the index page can be loaded, uses the correct templates
        and that the course list contains the test course.
        """

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("course_list", response.context)
        course_list = response.context["course_list"]
        self.assertTrue(course_list.filter(name="testcourse"))
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/index.html")

    def test_course_view(self):
        """
        Tests that the course instance index and front page can be loaded and
        uses the correct templates.
        """

        response = self.client.get(helpers.TestUrls.course_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/course.html")

    def test_plain_page_view(self):
        """
        Tests that a plain page with only cosmetic markup can be loaded and
        uses the correct templates.
        """

        response = self.client.get(helpers.TestUrls.plain_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/contentpage.html")
        self.assertTemplateUsed(response, "courses/lecture.html")

    def test_page_with_media(self):
        """
        Tests that a page with embedded media (file and image) can be loaded
        and uses the correct templates, including those of its embedded media.
        """

        response = self.client.get(helpers.TestUrls.media_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/contentpage.html")
        self.assertTemplateUsed(response, "courses/lecture.html")
        self.assertTemplateUsed(response, "courses/embedded-codefile.html")

    def test_page_with_checkbox_exercise(self):
        """
        Tests that a page with an embedded checkbox exercise can be loaded and
        uses the correct templates, including the checkbox exercise template
        chain.
        """

        response = self.client.get(helpers.TestUrls.checkbox_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/contentpage.html")
        self.assertTemplateUsed(response, "courses/lecture.html")
        self.assertTemplateUsed(response, "courses/exercise.html")
        self.assertTemplateUsed(response, "courses/checkbox-exercise.html")
        self.assertTemplateUsed(response, "feedback/feedbacks.html")

    def test_page_with_multiple_choice_exercise(self):
        """
        Tests that a page with an embedded mutliple choice exercise can be
        loaded and uses the correct templates, including the multiple choice
        exercise template chain.
        """

        response = self.client.get(helpers.TestUrls.multiple_choice_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/contentpage.html")
        self.assertTemplateUsed(response, "courses/lecture.html")
        self.assertTemplateUsed(response, "courses/exercise.html")
        self.assertTemplateUsed(response, "courses/multiple-choice-exercise.html")
        self.assertTemplateUsed(response, "feedback/feedbacks.html")

    def test_page_with_textfield_exercise(self):
        """
        Tests that a page with an embedded textfield exercise can be loaded and
        uses the correct templates, including the textfield exercise template
        chain.
        """

        response = self.client.get(helpers.TestUrls.textfield_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/contentpage.html")
        self.assertTemplateUsed(response, "courses/lecture.html")
        self.assertTemplateUsed(response, "courses/exercise.html")
        self.assertTemplateUsed(response, "courses/textfield-exercise.html")
        self.assertTemplateUsed(response, "feedback/feedbacks.html")

    def test_page_with_file_upload_exercise(self):
        """
        Tests that a page with an embedded file upload exercise can be loaded
        and uses the correct templates, including the file upload exercise
        template chain.
        """

        response = self.client.get(helpers.TestUrls.file_upload_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/contentpage.html")
        self.assertTemplateUsed(response, "courses/lecture.html")
        self.assertTemplateUsed(response, "courses/exercise.html")
        self.assertTemplateUsed(response, "courses/file-upload-exercise.html")
        self.assertTemplateUsed(response, "feedback/feedbacks.html")

    def test_page_with_template_exercise(self):
        """
        Tests that a page with an embedded repeated template exercise can be
        loaded and uses the correct templates, including the repeated template
        exercise template chain.
        """

        response = self.client.get(helpers.TestUrls.template_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/base.html")
        self.assertTemplateUsed(response, "courses/contentpage.html")
        self.assertTemplateUsed(response, "courses/lecture.html")
        self.assertTemplateUsed(response, "courses/exercise.html")
        self.assertTemplateUsed(response, "courses/repeated-template-exercise.html")
        self.assertTemplateUsed(response, "feedback/feedbacks.html")

    def test_pages_with_terms(self):
        """
        Tests that pages with embedded terms work. Repeated for a plain term,
        a term with a tab and a term with a link.
        """

        response = self.client.get(helpers.TestUrls.plain_term_page_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(helpers.TestUrls.tab_term_page_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(helpers.TestUrls.link_term_page_url)
        self.assertEqual(response.status_code, 200)

    def test_termbank_contents(self):
        """
        Tests that the three terms created in test setup can be found from the
        course instance termbank.
        """

        response = self.client.get(helpers.TestUrls.course_url)
        self.assertIn("termbank_contents", response.context)
        termbank = dict(response.context["termbank_contents"])
        self.assertEqual(len(termbank["P"]), 1)
        self.assertEqual(len(termbank["T"]), 2)
