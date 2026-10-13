from django.contrib import admin

from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
from reversion.admin import VersionAdmin

from ace.models import AceWidgetSettings, AcePlusWidgetSettings
from utils.management import CourseContentAdmin

# Register your models here.




class AceWidgetAdmin(VersionAdmin):

    content_type = "ACE"
    save_on_top = True
    list_display = ["slug", "course"]


class AcePlusWidgetAdmin(VersionAdmin):

    content_type = "ACE_PLUS"
    save_on_top = True
    list_display = ["slug", "course"]


admin.site.register(AceWidgetSettings, AceWidgetAdmin)
admin.site.register(AcePlusWidgetSettings, AcePlusWidgetAdmin)

