from django.db import models
from django.utils.translation import ugettext as _
from reversion.models import Version
from courses.models import ContentPage, CourseInstance


class FaqQuestion(models.Model):
    
    question = models.TextField(verbose_name=_("Question"))
    answer = models.TextField(verbose_name=_("Answer"))
    hook = models.SlugField(max_length=255, blank=False, allow_unicode=True, unique=True)

    def __str__(self):
        return "({}) {}".format(self.hook, self.question)
        
        
class FaqToInstanceLink(models.Model):
    question = models.ForeignKey(FaqQuestion, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    exercise = models.ForeignKey(ContentPage, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(
        verbose_name="Revision to display",
        blank=True,
        null=True
    )
    
    class Meta:
        unique_together = ("instance", "question", "exercise")
    
    def freeze(self, freeze_to=None):
        from faq.utils import regenerate_cache
        
        if self.revision is None:
            latest = Version.objects.get_for_object(self.question).latest("revision__date_created")
            self.revision = latest.revision_id
            
        
        
        
        

    