from django import template

register = template.Library()

# {% content_meta %}
@register.inclusion_tag("courses/content-meta.html")
def content_meta(course_slug, content, user, evaluation):
    return {"course_slug": course_slug, "content": content, "user": user,
            "evaluation": evaluation}

