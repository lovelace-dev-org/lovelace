from django.contrib import admin
from django.db.models import Q
from reversion.models import Version
from courses.models import Course, CourseInstance
from utils.access import determine_access, determine_media_access

#TODO: There's a loophole where staff members of any course A can gain access
#      to any course B's pages by embedding the course B page to a course A 
#      page. The behavior itself is necessary to complete the access chain. 
#      Editors must be prohibited from adding embedded links to pages they do
#      not have access to. 
class CourseContentAccess(admin.ModelAdmin):
    """
    This class adds access control based on 1) authorship and 2) staff membership
    on the relevant course. Staff membership follows both contentgraph links and 
    embedded page links. 
    
    The entire access chain:
    Course
    -> CourseInstance
      -> ContentGraph
        -> ContentPage
          -> EmbeddedLink
            -> ContentPage
    """
    
    content_type = ""

    @staticmethod
    def content_access_list(request, model, content_type=None):
        """
        Gets a queryset of content where the requesting user either:
        1) has edited the page previously
        2) belongs to the staff of a course that contains the content
           either as a contentgraph node or as an embedded page
        
        The content type is read from the content_type attribute. Child
        classes should set this attribute to control which type of 
        content is shown.         
        """        
        
        if content_type:
            qs = model.objects.filter(content_type=content_type)
        else:
            qs = model.objects.all()
            
        if request.user.is_superuser:
            return qs
        
        edited = Version.objects.get_for_model(model).filter(revision__user=request.user).values_list("object_id", flat=True)
        
        qs = qs.filter(
            Q(id__in=list(edited)) |
            Q(contentgraph__instance__course__staff_group__user=request.user) |
            Q(emb_embedded__parent__contentgraph__instance__course__staff_group__user=request.user)
        ).distinct()
        
        return qs

    def get_queryset(self, request):
        return CourseContentAccess.content_access_list(request, self.model, self.content_type).defer("content")
    
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_access(request.user, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_access(request.user, obj)
        
    #TODO: this solution is less garbage now, but we still need to rethink
    #      the entire contentgraph and embedded links structure. 
    #NOTE: this is now done in ContentPage save method
    #def save_model(self, request, obj, form, change):
        #"""
        #Need to call rendered_markup of the object for each context where it 
        #exists as latest version in order to create embedded page links. 
        #"""
        
        #super().save_model(request, obj, form, change)
        #contexts = self._find_contexts(obj)
        #for context in contexts:
            #obj.update_embedded_links(context["instance"])
        
    def _find_contexts(self, obj):
        """
        Find the context(s) (course instances) where this page is linked that 
        have not been frozen. 
        """
        
        instances = CourseInstance.objects.filter(contents__content=obj, contents__revision=None)
        contexts = []
        for instance in instances:
            context = {
                'course': instance.course,
                'course_slug': instance.course.slug,
                'instance': instance,
                'instance_slug': instance.slug,
            }
            contexts.append(context)
        
        return contexts        

    def _match_groups(self, user, obj):
        """
        Matches a user's groups to the staff groups of the target object.
        Returns True if the user is in the staff group of the course that
        is at the end of the access chain for the object.
        """
        
        if Course.objects.filter(
            Q(courseinstance__contents__content=obj) |
            Q(courseinstance__contents__content__embedded_pages=obj)
        ).filter(staff_group__user=user):
            return True
        
        return False


class CourseMediaAccess(admin.ModelAdmin):
    
    @staticmethod
    def media_access_list(request, model):
        qs = model.objects.all()
        
        if request.user.is_superuser:
            return qs
        
        
        edited = Version.objects.get_for_model(model).filter(revision__user=request.user).values_list("object_id", flat=True)
        
        user_groups = request.user.groups.get_queryset()
        
        return qs.filter(
            Q(id__in=list(edited)) |
            Q(coursemedialink__instance__course__staff_group__in=user_groups)
        ).distinct()
    
    def get_queryset(self, request):
        return CourseMediaAccess.media_access_list(request, self.model)
    
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_media_access(request.user, obj)
        
    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return determine_media_access(request.user, obj)

    def _match_groups(self, user, obj):
        
        user_groups = user.groups.get_queryset()
        if obj.coursemedialink_set.get_queryset().filter(instance__course__staff_group__in=user_groups).distinct():
            return True
        
        return False
