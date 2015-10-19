from django import template

register = template.Library()

# {% show_basic_stats %}
@register.inclusion_tag("stats/basic_answer_stats.html")
def show_basic_stats(basic_stats):
    return basic_stats

# {% show_piechart %}
@register.inclusion_tag("stats/piechart.html")
def show_piechart(piechart):
    return piechart
 
