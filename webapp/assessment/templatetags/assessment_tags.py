from django import template

register = template.Library()


@register.filter
def points_widget(form, bullet):
    return form.points_widget(bullet)


@register.filter
def comment_widget(form, bullet):
    return form.comment_widget(bullet)


@register.filter
def bullet_score(assessment, bullet):
    return assessment["bullet_index"].get(str(bullet.id), {}).get("scored_points", 0)


@register.filter
def bullet_comment(assessment, bullet):
    return assessment["bullet_index"].get(str(bullet.id), {}).get("comment", "")


@register.filter
def bullet_lookup(bullet_index, bullet_id):
    return bullet_index.get(bullet_id)
