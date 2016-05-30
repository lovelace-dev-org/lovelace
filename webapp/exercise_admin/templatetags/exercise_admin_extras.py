from django import template
from django.utils.safestring import mark_safe

from courses.models import default_fue_timeout

register = template.Library()

@register.inclusion_tag('exercise_admin/file-upload-exercise-test-tab.html')
def test_tab(test_obj, stages_list, jstemplate=False):
    if not jstemplate:
        return {'test': test_obj, 'stages': stages_list,}

    class TemplateCommand:
        id = "SAMPLE_COMMAND_ID"
        ordinal_number = "SAMPLE_COMMAND_ORDINAL_NUMBER"
        command_line = "New command"
        timeout = default_fue_timeout()

    class TemplateStage:
        id = "SAMPLE_STAGE_ID"
        ordinal_number = "SAMPLE_STAGE_ORDINAL_NUMBER"
        name = "New stage"

    class TemplateTest:
        id = "SAMPLE_TEST_ID"
        name = "New test"

    return {'test': TemplateTest, 'stages': [(TemplateStage, [(TemplateCommand, [])])]}

@register.inclusion_tag('exercise_admin/file-upload-exercise-include-file-tr.html')
def include_file_tr(include_file, jstemplate=False):
    if not jstemplate:
        return {'include_file': include_file,}

    class IncludeFile:
        id = "SAMPLE_ID"
        description = "SAMPLE_DESCRIPTION"
        file_settings = {
            "name" : "SAMPLE_NAME",
            "purpose" : "SAMPLE_PURPOSE",
            "get_purpose_display" : "SAMPLE_GET_PURPOSE_DISPLAY",
            "chown_settings" : "SAMPLE_CHOWN_SETTINGS",
            "chgrp_settings" : "SAMPLE_CHGRP_SETTINGS",
        }            

    return {'include_file' : IncludeFile}

@register.inclusion_tag('exercise_admin/file-upload-exercise-include-file-popup.html')
def include_file_popup(include_file, popup_title, jstemplate=False):
    if not jstemplate:
        return {
            'include_file': include_file,
            'popup_title' : popup_title,
        }

    class IncludeFile:
        id = "SAMPLE_ID"
        default_name = "SAMPLE_DEFAULT_NAME"
        description = "SAMPLE_DESCRIPTION"
        file_settings = {
            "name" : "SAMPLE_NAME",
            "chmod_settings" : "SAMPLE_CHMOD_SETTINGS"
        }
        fileinfo = {
            "url" : None,
        }

    return {
        'include_file' : IncludeFile,
        'popup_title' : 'SAMPLE_POPUP_TITLE',
    }

@register.simple_tag()
def lang_reminder(lang_code):
    s = '<span class="language-code-reminder" title="The currently selected translation">{}</span>'.format(lang_code)
    return mark_safe(s)

@register.simple_tag()
def get_translated_field(model, variable, lang_code):
    if model:
        return getattr(model, '{}_{}'.format(variable, lang_code))
    else:
        return ''
