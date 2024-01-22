from reversion import revisions as reversion
from reversion.admin import VersionAdmin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from assessment.models import AssessmentBullet, AssessmentSection, AssessmentSheet

# Register your models here.
reversion.register(AssessmentSheet, follow=["assessmentbullet_set", "assessmentsection_set"])
reversion.register(AssessmentBullet)
reversion.register(AssessmentSection)


class AssessmentBulletInline(TranslationTabularInline):
    model = AssessmentBullet
    extra = 1


class AssessmentAdmin(TranslationAdmin, VersionAdmin):
    list_display = ("title",)
    inlines = [AssessmentBulletInline]
