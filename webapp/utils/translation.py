from contextlib import contextmanager
from django.utils import translation

@contextmanager
def user_language(user):
    user_lang = user.userprofile.language_preference
    if user_lang is None:
        yield
    else:
        current_lang = translation.get_language()
        translation.activate(user_lang)
        try:
            yield
        finally:
            translation.activate(current_lang)




