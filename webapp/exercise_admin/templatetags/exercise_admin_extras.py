from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from courses.models import default_fue_timeout

from ..utils import get_default_lang, get_lang_list

register = template.Library()

@register.inclusion_tag('exercise_admin/hint.html')
def hint_tr(hint, jstemplate=False):
    if not jstemplate:
        return {'hint' : hint,}

    lang_list = get_lang_list()
    
    class TemplateHint:
        id = "SAMPLE_ID"
        tries_to_unlock = 0

        def __init__(self):
            for lang_code, _ in lang_list:
                setattr(self, 'hint_{}'.format(lang_code), "")

    return {"hint" : TemplateHint()}

@register.inclusion_tag('exercise_admin/file-upload-exercise-test-tab.html')
def test_tab(test_obj, stages_list, instance_files, exercise_files, jstemplate=False):
    if not jstemplate:
        return {'test': test_obj, 'stages': stages_list, 'instance_files': instance_files,
                'exercise_files': exercise_files}

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

    return {'test': TemplateTest(), 'stages': [(TemplateStage(), [(TemplateCommand(), [])])],
            'instance_files': [], 'exercise_files': []}

@register.filter
def has_instance_file(test, instance_file):
    if instance_file.include_file.id in test.required_instance_files.all().values_list('id', flat=True):
        return True
    return False

@register.filter
def has_exercise_file(test, exercise_file):
    if exercise_file.id in test.required_files.all().values_list('id', flat=True):
        return True
    return False

@register.inclusion_tag('exercise_admin/file-upload-exercise-include-file-tr.html')
def include_file_tr(include_file, jstemplate=False):
    if not jstemplate:
        return {'include_file': include_file,}

    lang_list = get_lang_list()

    class TemplateFileSettings:
        purpose = "SAMPLE_PURPOSE"
        get_purpose_display = "SAMPLE_GET_PURPOSE_DISPLAY"
        chown_settings = "SAMPLE_CHOWN_SETTINGS"
        chgrp_settings = "SAMPLE_CHGRP_SETTINGS"
        
        def __init__(self):
            for lang_code, _ in lang_list:
                setattr(self, 'name_{}'.format(lang_code), "SAMPLE_NAME_{}".format(lang_code))

    class TemplateIncludeFile:
        id = "SAMPLE_ID"
        file_settings = TemplateFileSettings()

        def __init__(self):
            for lang_code, _ in lang_list:
                setattr(self, 'description_{}'.format(lang_code), "SAMPLE_DESCRIPTION_{}".format(lang_code))

    return {'include_file' : TemplateIncludeFile()}

@register.inclusion_tag('exercise_admin/file-upload-exercise-include-file-popup.html')
def include_file_popup(include_file, create=False, jstemplate=False):
    if not jstemplate:
        return {
            'include_file': include_file,
            'create' : create,
        }
    lang_list = get_lang_list()

    class TemplateFileSettings:
        purpose = "INPUT"
        chown_settings = "OWNED"
        chgrp_settings = "OWNED"
        chmod_settings = "rw-rw-rw-"
        
        def __init__(self):
            for lang_code, _ in lang_list:
                setattr(self, 'name_{}'.format(lang_code), "")

    class TemplateFileInfo:
        url = None
    
    class TemplateIncludeFile:
        id = "SAMPLE_ID"
        file_settings = TemplateFileSettings()
        
        def __init__(self):
            for lang_code, _ in lang_list:
                setattr(self, 'default_name_{}'.format(lang_code), "")
                setattr(self, 'description_{}'.format(lang_code), "")
                setattr(self, 'fileinfo_{}'.format(lang_code), TemplateFileInfo())

    return {
        'include_file' : TemplateIncludeFile(),
        'create' : create,
    }

@register.inclusion_tag('exercise_admin/file-upload-exercise-instance-file-tr.html')
def instance_file_tr(instance_file_link, jstemplate=False):
    if not jstemplate:
        return {'instance_file_link': instance_file_link,}
    
    lang_list = get_lang_list()
    
    class TemplateFileSettings:
        def __init__(self):
            self.get_purpose_display = "SAMPLE_GET_PURPOSE_DISPLAY"
            for lang_code, _ in lang_list:
                setattr(self, 'name_{}'.format(lang_code), "SAMPLE_NAME_{}".format(lang_code))

    class TemplateCourseInstance:
        def __init__(self):
            self.name = "SAMPLE_INSTANCE_NAME"
                    
    class TemplateInstanceFile:
        def __init__(self):
            self.id = "SAMPLE_ID"
            self.instance = TemplateCourseInstance()
            for lang_code, _ in lang_list:
                setattr(self, 'description_{}'.format(lang_code), "SAMPLE_DESCRIPTION_{}".format(lang_code))

    class TemplateInstanceIncludeFileToExerciseLink:
        def __init__(self):
            self.file_settings = TemplateFileSettings()
            self.include_file = TemplateInstanceFile()
                
    return {
        'instance_file_link' : TemplateInstanceIncludeFileToExerciseLink(),
    }

@register.inclusion_tag('exercise_admin/file-upload-exercise-edit-instance-file.html')
def edit_instance_file(create, instances):
    lang_list = get_lang_list()
    
    class TemplateInstanceFile:
        def __init__(self, create):
            if create:
                self.id = "SAMPLE_CREATE_ID"
                for lang_code, _ in lang_list:
                    setattr(self, 'default_name_{}'.format(lang_code), "")
                    setattr(self, 'description_{}'.format(lang_code), "")
            else:
                self.id = "SAMPLE_ID"
                for lang_code, _ in lang_list:
                    setattr(self, 'default_name_{}'.format(lang_code), "SAMPLE_DEFAULT_NAME_{}".format(lang_code))
                    setattr(self, 'description_{}'.format(lang_code), "SAMPLE_DESCRIPTION_{}".format(lang_code))
    
    return {
        'instance_file' : TemplateInstanceFile(create),
        'create' : create,
        'instances' : instances,
    }

@register.inclusion_tag('exercise_admin/file-upload-exercise-edit-file-link.html')
def edit_instance_file_link(linked):
    lang_list = get_lang_list()

    class TemplateInstanceFile:
        def __init__(self, linked):
            if linked:
                self.id = "SAMPLE_LINKED_ID"
                for lang_code, _ in lang_list:
                    setattr(self, 'default_name_{}'.format(lang_code), "SAMPLE_DEFAULT_NAME_{}".format(lang_code))
            else:
                self.id = "SAMPLE_ID"
                for lang_code, _ in lang_list:
                    setattr(self, 'default_name_{}'.format(lang_code), "SAMPLE_DEFAULT_NAME_{}".format(lang_code))
    
    class TemplateInstanceFileLink:
        def __init__(self, linked):
            if linked:
                self.chmod_settings = "SAMPLE_CHMOD_SETTINGS"
                for lang_code, _ in lang_list:
                    setattr(self, 'name_{}'.format(lang_code), "SAMPLE_NAME_{}".format(lang_code))
            else:
                self.chmod_settings = "rw-rw-rw-"
                for lang_code, _ in lang_list:
                    setattr(self, 'name_{}'.format(lang_code), "")

    return {
        "instance_file" : TemplateInstanceFile(linked),
        "instance_file_link" : TemplateInstanceFileLink(linked),
        "linked" : linked
    }

@register.inclusion_tag('exercise_admin/file-upload-exercise-instance-file-popup-tr.html')
def instance_file_popup_tr(linked):
    lang_list = get_lang_list()
    
    class TemplateFileInfo:
        def __init__(self, linked, lang_code):
            self.url = "SAMPLE_URL_{}".format(lang_code)
            self.url_css_class = "SAMPLE_URL_CSS_CLASS_{}".format(lang_code)
    
    class TemplateInstanceFile:
        def __init__(self, linked):
            if linked:
                self.id = "SAMPLE_LINKED_ID"
            else:
                self.id = "SAMPLE_ID"
            for lang_code, _ in lang_list:
                setattr(self, 'default_name_{}'.format(lang_code), "SAMPLE_DEFAULT_NAME_{}".format(lang_code))
                setattr(self, 'fileinfo_{}'.format(lang_code), TemplateFileInfo(linked, lang_code))
            self.instance = "SAMPLE_INSTANCE"

    class TemplateFileSettings:
        def __init__(self, linked):
            if linked:
                for lang_code, _ in lang_list:
                    setattr(self, 'name_{}'.format(lang_code), "SAMPLE_NAME_{}".format(lang_code))
            else:
                for lang_code, _ in lang_list:
                    setattr(self, 'name_{}'.format(lang_code), "")
                
    return {
        'instance_file' : TemplateInstanceFile(linked),
        'file_settings' : TemplateFileSettings(linked),
        'linked' : linked,
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

@register.assignment_tag()
def get_default_language():
    return get_default_lang()
