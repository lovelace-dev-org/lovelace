from django.contrib import admin
from reversion import revisions as reversion
from reversion.admin import VersionAdmin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from assessment.models import *

# Register your models here.
reversion.register(AssessmentSheet, follow=[
    "assessmentbullet_set"
    "assessmentsection_set"
])
reversion.register(AssessmentBullet)

class AssessmentBulletInline(TranslationTabularInline):
    model = AssessmentBullet
    extra = 1
    

class AssessmentAdmin(TranslationAdmin, VersionAdmin):
    
    list_display = ("title", )
    inlines = [AssessmentBulletInline]
    
    
