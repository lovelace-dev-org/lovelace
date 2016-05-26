from django import template

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
