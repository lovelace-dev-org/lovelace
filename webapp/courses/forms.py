import os.path
import re
import django.conf
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Count
from django import forms
from django.forms import fields
from django.utils.text import slugify
from django.utils.translation import gettext as _
from modeltranslation.forms import TranslationModelForm
from utils.formatters import display_name
from utils.management import add_translated_charfields
import courses.models as cm

class TextfieldExerciseForm(forms.Form):
    
    pass

# http://jacobian.org/writing/dynamic-form-generation/
class MultipleChoiceExerciseForm(forms.Form):
    pass

class CheckboxExerciseForm(forms.Form):
    pass

class FileUploadExerciseForm(forms.Form):
    pass

class CodeInputExerciseForm(forms.Form):
    pass

class CodeReplaceExerciseForm(forms.Form):
    pass
  

class FileEditForm(forms.ModelForm):
    
    def get_initial_for_field(self, field, field_name):

        default_value = super().get_initial_for_field(field, field_name)
        if isinstance(field, fields.FileField) and default_value:
            default_value.media_slug = self.initial.get("name")
            default_value.field_name = field_name
            default_value.filename = os.path.basename(default_value.name)
            
        return default_value
        
        
class RepeatedTemplateExerciseBackendForm(forms.ModelForm):
    
    def get_initial_for_field(self, field, field_name):
        
        default_value = super().get_initial_for_field(field, field_name)        
        if isinstance(field, fields.FileField) and default_value:
            default_value.exercise_id = self.initial.get("exercise")
            default_value.field_name = field_name
            default_value.filename = os.path.basename(default_value.name)

        return default_value

# TODO: add a validator for broken markup
class ContentForm(forms.ModelForm):
    
    
    def _validate_links(self, value, lang):
        """
        Goes through the given content field and checks that every embedded
        link to other pages, media files and terms matches an existing one.
        If links to missing entities are found, these are reported as a
        validation error. 
        """
        
        import courses.blockparser as blockparser
        import courses.markupparser as markupparser
        from courses.models import ContentPage, CourseMedia, Term
        
        missing_pages = []
        missing_media = []
        missing_terms = []
        messages = []
        
        page_links, media_links = markupparser.LinkParser.parse(value)
        for link in page_links:
            if not ContentPage.objects.filter(slug=link):
                missing_pages.append(link)
                messages.append("Content matching {} does not exist".format(link))
                
        for link in media_links:
            if not CourseMedia.objects.filter(name=link):
                missing_media.append(link)
                messages.append("Media matching {} does not exist".format(link))
                
        term_re = blockparser.tags["term"].re
        
        term_links = set([match.group("term_name") for match in term_re.finditer(value)])
        
        for link in term_links:
            if not Term.objects.filter(**{"name_" + lang: link}):
                missing_terms.append(link)
                messages.append("Term matching {} does not exist".format(link))
                                
        if messages:
            raise ValidationError(messages)
    
    def clean(self):
        cleaned_data = super().clean()
        for lang_code, _ in django.conf.settings.LANGUAGES:
            try:
                self._validate_links(cleaned_data["content_" + lang_code], lang_code)
            except ValidationError as e:
                self.add_error("content_" + lang_code, e)
    
        
class TextfieldAnswerForm(forms.ModelForm):
    
    def _check_regexp(self, exp):
        """
        Validates a regular expression by trying to compile it. Skipped for
        non-regexp answers.
        """
        
        try:
            re.compile(exp)
        except re.error as e:
            raise ValidationError("Broken regexp: {}".format(e))

    def clean(self):
        cleaned_data = super().clean()
        for lang_code, _ in django.conf.settings.LANGUAGES:
            try:
                self._check_regexp(cleaned_data["answer_" + lang_code])
            except ValidationError as e:
                self.add_error("answer_" + lang_code, e)
            
        
class InstanceForm(forms.ModelForm):
    
    def clean(self):
        cleaned_data = super().clean()
        default_lang = django.conf.settings.LANGUAGE_CODE
        slug = slugify(cleaned_data.get("name_{}".format(default_lang)), allow_unicode=True)
        if slug == cleaned_data["course"].slug:
            raise ValidationError("Instance cannot have the same slug as its course")

            
class InstanceSettingsForm(TranslationModelForm):

    class Meta:
        model = cm.CourseInstance
        fields = ["name", "email", "start_date", "end_date", "primary", "max_group_size", "manual_accept", "welcome_message", "content_license", "license_url"]
        
    def __init__(self, *args, **kwargs):
        available_content = kwargs.pop("available_content")
        super().__init__(*args, **kwargs)
        
        self.fields["frontpage"] = forms.ChoiceField(
            widget = forms.Select,
            label = _("Choose frontpage"),
            choices = [(0, _("--NO-FRONTPAGE--")), ] + [(c.id, c.name) for c in available_content]
        )
    

class InstanceFreezeForm(forms.Form):
    
    freeze_to = forms.DateField(
        label=_("Freeze instance contents to date:"),
        required=True
    )
    
class InstanceCloneForm(forms.ModelForm):

    class Meta:
        model = cm.CourseInstance
        fields = ["start_date", "end_date"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        add_translated_charfields(
            self,
            "name",
            _("Instance default name ({lang})"),
            _("Alternative name ({lang})"),
        )
    
class NewContentNodeForm(forms.ModelForm):

    class Meta:
        model = cm.ContentGraph
        fields = ["publish_date", "deadline", "scored", "visible", "evergreen"]
        
    make_child = forms.BooleanField(
        label=_("Make this node a child of the selected node"),
        required=False
    )
    
    new_page_name = forms.CharField(
        label=_("Name for new page (in default language)"),
        required=False
    )
    
    active_node = forms.IntegerField(
        widget=forms.HiddenInput,
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        available_content = kwargs.pop("available_content")
        super().__init__(*args, **kwargs)
        
        self.fields["content"] = forms.ChoiceField(
            widget = forms.Select,
            label = _("Choose content to link"),
            choices = [(0, _("----NEW--PAGE----")), ] + [(c.id, c.name) for c in available_content]
        )


class NodeSettingsForm(forms.ModelForm):
    
    class Meta:
        model = cm.ContentGraph
        fields = ["publish_date", "deadline", "scored", "late_rule", "visible", "evergreen"]
        
    active_node = forms.IntegerField(
        widget=forms.HiddenInput,
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        available_content = kwargs.pop("available_content")
        super().__init__(*args, **kwargs)
        
        self.fields["content"] = forms.ChoiceField(
            widget = forms.Select,
            label = _("Choose content to link"),
            choices = [(0, _("----NEW--PAGE----")), ] + [(c.id, c.name) for c in available_content]
        )
        
class IndexEntryForm(TranslationModelForm):

    class Meta:
        pass
        
        
class GroupForm(forms.ModelForm):
    class Meta:
        model = cm.StudentGroup
        fields = ["name"]
        
    def __init__(self, *args, **kwargs):
        staff = kwargs.pop("staff")
        super().__init__(*args, **kwargs)

        self.fields["supervisor"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose student to add"),
            choices=[(0, _('-- no supervisor --')), ] + [(s.id, display_name(s)) for s in staff]
        )
        
        
class GroupConfigForm(forms.ModelForm):
    class Meta:
        model = cm.StudentGroup
        fields = ["name"]
        
class GroupInviteForm(forms.Form):
    
    def clean(self):
        cleaned_data = super().clean()
        i = 0
        while True:
            field_name = "invite-{}".format(i)
            i += 1
            try:
                username = cleaned_data[field_name]
                if not username:
                    continue
                user = cm.User.objects.get(username=username)
                assert cm.CourseEnrollment.objects.filter(
                    instance=self.valid_for_instance,
                    student=user
                ).exists()
                assert not cm.StudentGroup.objects.annotate(member_count=Count("members")).filter(
                    member_count__gte=2,
                    members=user,
                    instance=self.valid_for_instance,
                ).exists()
            except KeyError:
                break
            except (cm.User.DoesNotExist, AssertionError) as e:
                print(e)
                self.add_error(field_name, _("Cannot invite this user"))
            else:
                self.invited_users.append(user)
        
    def is_valid(self, for_instance=None):
        self.valid_for_instance = for_instance
        return super().is_valid()
    
    def __init__(self, *args, **kwargs):
        slots = kwargs.pop("slots")
        self.invited_users = []
        super().__init__(*args, **kwargs)
        
        for i in range(slots):
            self.fields["invite-{}".format(i)] = forms.CharField(
                label=_("Invitee {}").format(i + 1),
                required=False
            )
            
class GroupMemberForm(forms.Form):

    def __init__(self, *args, **kwargs):
        students = kwargs.pop("students")
        super().__init__(*args, **kwargs)
        
        self.fields["student"] = forms.ChoiceField(
            widget=forms.Select,
            label=_("Choose student to add"),
            choices=[(s.id, display_name(s)) for s in students]
        )


class CalendarConfigForm(forms.ModelForm):
    
    class Meta:
        model = cm.Calendar
        fields = ["allow_multiple"]
    

    def __init__(self, *args, **kwargs):
        available_content = kwargs.pop("available_content")
        super().__init__(*args, **kwargs)
        self.fields["related_content"] = forms.ChoiceField(
            widget = forms.Select,
            label = _("Choose content to link"),
            choices = [(0, _('-- no content --')), ] + [(c.id, c.name) for c in available_content]
        )
    
    
class CalendarSchedulingForm(forms.Form):
    start = forms.DateTimeField(
        label=_("Starting date and time"),
        required=True,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.widgets.DateTimeInput(
            attrs={"type": "datetime-local"}
        )
    )
    event_duration = forms.DurationField(
        label=_("Duration of each event (minutes)"),
        required=True,
        widget=forms.widgets.NumberInput()
    )
    event_slots = forms.IntegerField(
        label=_("Number of slots per event"),
        required=True,
    )
    event_count = forms.IntegerField(
        label=_("Number of events to add"),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        add_translated_charfields(
            self,
            "event_name",
            _("Default name ({lang}):"),
            _("Alternative name ({lang}):")
        )

    
class MessageForm(forms.Form):
    title = forms.CharField(
        label=_("Message title"),
        required=True,
    )
    content = forms.CharField(
        label=_("Message content"),
        required=True,
        widget=forms.Textarea(attrs={"class": "generic-textfield", "rows": 5})
    )
