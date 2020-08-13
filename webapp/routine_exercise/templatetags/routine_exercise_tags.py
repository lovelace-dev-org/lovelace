from django import template

import courses.markupparser as markupparser

register = template.Library()

@register.filter
def rendered_question(question):
    rendered_text = question.template.content.format(
        **question.generated_json["formatdict"]
    )
    marked_text = "".join(
        markupparser.MarkupParser.parse(rendered_text)
    ).strip().replace("<div", "<span").replace("</div", "</span")
    return marked_text