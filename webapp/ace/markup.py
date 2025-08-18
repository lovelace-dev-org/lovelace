import re
from django.template import loader
from courses import markupparser
from courses.widgets import AnswerWidgetRegistry
from ace.models import AcePlusWidgetSettings

class AcePlusMarkup(markupparser.Markup):

    name = "Ace Plus"
    shortname = "ace-plus"
    description = "Configurable Ace + Preview widget."
    regexp = re.compile(r"^\<\!aceplus\=(?P<key_slug>[^\s>]+)\>\s*$")
    markup_class = "embedded item"
    example = "<!aceplus=ace-demo>"
    inline = False
    allow_inline = False
    is_editable = True
    has_reference = True

    @classmethod
    def block(cls, block, settings, state):
        instance = state["context"].get("instance")
        key_slug = settings["key_slug"]
        widget = AnswerWidgetRegistry.get_widget("ace-plus", instance, key_slug)
        yield widget.render(state["context"])

    @classmethod
    def settings(cls, matchobj, state):
        settings = {"key_slug": matchobj.group("key_slug")}
        return settings

    @classmethod
    def markup_from_dict(cls, form_data):
        return f"<!aceplus={form_data['key_slug']}>"


def register_markups():
    markupparser.MarkupParser.register_markup(AcePlusMarkup)
