import django.conf


def get_default_lang():
    settings = django.conf.settings
    # default_lang = settings.get('LANGUAGE_CODE', '')
    default_lang = settings.LANGUAGE_CODE
    return default_lang


def get_lang_list():
    settings = django.conf.settings
    # lang_list = settings.get('LANGUAGES', [])
    lang_list = settings.LANGUAGES
    return lang_list
