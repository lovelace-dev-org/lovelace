import re
from django.template import loader
from courses import markupparser
from assessment.models import AssessmentToExerciseLink
from assessment.utils import get_sectioned_sheet


class AssessmentMarkup(markupparser.Markup):
    name = "Assessment"
    shortname = "assessment"
    description = "Embedded view of an assessment sheet."
    regexp = re.compile(r"^\<\!assessment\=(?P<exercise_slug>[^\s>]+)\>\s*$")
    markup_class = "embedded item"
    example = "<!assessment=dtc-exercise-1>"
    inline = False
    allow_inline = False
    is_editable = True
    has_reference = True

    @classmethod
    def block(cls, block, settings, state):
        instance = state["context"].get("instance")
        sheet_link = AssessmentToExerciseLink.objects.get(
            exercise__slug=settings["exercise_slug"],
            instance=instance
        )
        if sheet_link:
            sheet, by_section = get_sectioned_sheet(sheet_link)
        else:
            by_section = {}
            sheet = None

        t = loader.get_template("assessment/embedded-view.html")
        c = {
            "sheet": sheet,
            "bullets_by_section": by_section,
        }
        yield t.render(c)

    @classmethod
    def settings(cls, matchobj, state):
        settings = {"exercise_slug": matchobj.group("exercise_slug")}
        return settings

    @classmethod
    def markup_from_dict(cls, form_data):
        return f"<!assessment={form_data['exercise_slug']}>"

def register_markups():
    markupparser.MarkupParser.register_markup(AssessmentMarkup)
