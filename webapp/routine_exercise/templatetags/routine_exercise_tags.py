from django import template

import courses.markupparser as markupparser

register = template.Library()


@register.filter
def rendered_question(question):
    try:
        rendered_text = question.template.content.format(**question.generated_json["formatdict"])
    except KeyError:
        rendered_text = question.template.content.replace("{{", "{").replace("}}", "}")
    parser = markupparser.MarkupParser()
    marked_text = (
        "".join(block[1] for block in parser.parse(rendered_text))
        .strip()
        .replace("<div", "<span")
        .replace("</div", "</span")
    )
    return marked_text
