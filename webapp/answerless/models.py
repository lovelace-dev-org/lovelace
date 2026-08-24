from django.db import models
from django.urls import reverse
from django.template import loader
from django.utils.translation import gettext_lazy as _

import courses.models as cm

# Create your models here.

class AnswerlessTask(cm.ContentPage):

    class Meta:
        verbose_name = "answerless task"
        proxy = True

    default_answer_widget = "answerless"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "ANSWERLESS_TASK"
        super().save(*args, **kwargs)

    def get_rendered_content(self, context):
        """
        Includes the answerless tas extra template into the rendered markup. This adds
        teacher options for creating entries for students.
        """

        content = cm.ContentPage._get_rendered_content(self, context)
        # t = loader.get_template("answerless/answerless-task-extra.html")
        return content #+ [("extra", t.render(context), -1, 0)]

    def get_question(self, context):
        """
        Gets the question part of the task, no changes to the default.
        """

        return None

    def get_admin_change_url(self):
        """
        Returns admin change url for the model instance.
        """

        adminized_type = self.content_type.replace("_", "").lower()
        return reverse(f"admin:answerless_{adminized_type}_change", args=(self.id,))

    def get_choices(self, revision=None):
        """
        This task type has a separate implementation for handling this behavior, so just returns
        None.
        """

        return

    def get_staff_extra(self, context):
        """
        Adds a link to attempt management page to the task's staff tools.
        """

        options = cm.ContentPage.get_staff_extra(self, context)
        options.append((
            _("Add student entry"),
            "add-answerless-entry",
            "side-panel",
            reverse("answerless:add_student_entry", kwargs={
                "course": context["course"],
                "instance": context["instance"],
                "parent": context["parent"],
                "content": self,
            })
        ))
        return options

    def save_answer(self, user, ip, answer, files, instance, revision):

        answer_object = AnswerlessEntry(
            user=user,
            exercise=self,
            instance=instance,
            revision=revision,
            answerer_ip=ip,
            note=answer["note"].replace("\r", "")
        )
        answer_object.save()
        return answer_object

    def check_answer(self, link, user, answer, files, answer_object):
        return {
            "evaluation": True,
            "quotient": answer["quotient"]
        }

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            return AnswerlessEntry.objects.filter(
                user=user,
                exercise=self,
            )
        else:
            return AnswerlessEntry.objects.filter(
                instance=instance,
                user=user,
                exercise=self,
            )


class AnswerlessEntry(cm.UserAnswer):

    exercise = models.ForeignKey(AnswerlessTask, on_delete=models.CASCADE)
    note = models.TextField(blank=True, default="")


cm.ContentPage.register_content_type(
    "ANSWERLESS_TASK", AnswerlessTask, None, AnswerlessEntry,
)

def export_models(instance, export_target):
    pass

def get_import_list():
    return [
        "AnswerlessTask"
    ]
