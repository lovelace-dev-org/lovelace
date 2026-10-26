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
        course = state["context"]["course"]
        slug = settings["slug"]
        widget = AnswerWidgetRegistry.get_widget("ace-plus", course, slug)
        yield widget.render(state["context"])

    @classmethod
    def settings(cls, matchobj, state):
        settings = {"slug": matchobj.group("key_slug")}
        return settings

    @classmethod
    def markup_from_dict(cls, form_data):
        return f"<!aceplus={form_data['slug']}>"

    @classmethod
    def build_links(cls, block, matchobj, instance, links):
        slug = matchobj.group("key_slug")
        links["aceplus"].append(slug)


def register_markups():
    markupparser.MarkupParser.register_markup(AcePlusMarkup)
    markupparser.LinkParser.register_markup(AcePlusMarkup)
