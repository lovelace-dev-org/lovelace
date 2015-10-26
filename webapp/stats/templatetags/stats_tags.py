from django import template

SUMMARY_TITLE = "Summary for all courses"
SUMMARY_ID = "summary"

register = template.Library()

# {% show_basic_stats %}
@register.inclusion_tag("stats/basic_answer_stats.html")
def show_basic_stats(basic_stats):
    return basic_stats

# {% show_piechart %}
@register.inclusion_tag("stats/piechart.html")
def show_piechart(piechart):
    return piechart
 
# {% user_answers_title %}
@register.inclusion_tag("stats/user_answers_title.html")
def user_answers_title(course):
    return {
        "title": course.name if course else SUMMARY_TITLE,
        "heading_id": course.slug + "-course" if course else SUMMARY_ID,
    }
        
        
