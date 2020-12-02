from django.contrib import admin
from django.db.models import Q
from modeltranslation.admin import TranslationAdmin
from reversion.admin import VersionAdmin
from reversion.models import Version
from reversion import revisions as reversion
from courses.models import ContentPage
from faq.models import FaqQuestion
from utils.management import CourseContentAdmin

reversion.register(FaqQuestion)

class FaqAdmin(TranslationAdmin, VersionAdmin):
    
    search_fields = ("hook",)
    list_display = ("hook", "question",)
    list_per_page = 500
    ordering = ("question",)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
            
        edited = Version.objects.get_for_model(FaqQuestion).filter(revision__user=request.user).values_list("object_id", flat=True)
        
        content_access = CourseContentAdmin.content_access_list(request, ContentPage).values_list("id", flat=True)
        
        return qs.filter(
            Q(id__in=list(edited)) |
            Q(exercise__id__in=list(content_access))
        )
        
admin.site.register(FaqQuestion, FaqAdmin)
        
            
        
        
        
        
