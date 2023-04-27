import os
import shutil
from django.conf import settings
from django.test import StaticLiveServerTestCase
from courses.testhelpers import TestSettingsNotUsed


class StudentViewTests(StaticLiveServerTestCase):
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
