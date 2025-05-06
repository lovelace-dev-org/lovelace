from django import template
register = template.Library()

@register.simple_tag
def option_checked(answers, handle, key):
    return "checked" if key in answers.get(handle, "") else ""

@register.inclusion_tag("multiexam/answered-exam.html", takes_context=True)
def answered_exam_choices(context, answer_object):
    script = answer_object.attempt.exam_script
    summary = {}
    for handle, question in script:
        chosen = []
        for choice in answer_object.answers[handle]:
            chosen.append(question["options"][choice])
        summary[handle] = chosen

    return {
        "answer_summary": summary.values()
    }



