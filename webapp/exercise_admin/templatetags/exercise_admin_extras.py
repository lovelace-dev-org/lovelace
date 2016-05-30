from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from courses.models import default_fue_timeout

from ..utils import get_lang_list

register = template.Library()

@register.inclusion_tag('exercise_admin/file-upload-exercise-test-tab.html')
def test_tab(test_obj, stages_list, jstemplate=False):
    if not jstemplate:
        return {'test': test_obj, 'stages': stages_list,}

    lang_list = get_lang_list()

    class TemplateCommand:
        id = "SAMPLE_COMMAND_ID"
        ordinal_number = "SAMPLE_COMMAND_ORDINAL_NUMBER"
        #command_line = "New command"
        timeout = default_fue_timeout()

        def __init__(self):
            for lang_code, lang_name in lang_list:
                setattr(self, 'command_line_{}'.format(lang_code), "New command ({})".format(lang_name))
                setattr(self, 'input_text_{}'.format(lang_code), "")

    class TemplateStage:
        id = "SAMPLE_STAGE_ID"
        ordinal_number = "SAMPLE_STAGE_ORDINAL_NUMBER"
        #name = "New stage"

        def __init__(self):
            for lang_code, _ in lang_list:
                setattr(self, 'name_{}'.format(lang_code), "New stage")

    class TemplateTest:
        id = "SAMPLE_TEST_ID"
        name = "New test"

    return {'test': TemplateTest(), 'stages': [(TemplateStage(), [(TemplateCommand(), [])])]}

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
