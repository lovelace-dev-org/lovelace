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

# {% sortable_table_header %}
@register.inclusion_tag("stats/sortable_table_header.html")
def sortable_table_header(course, header, column):
    return {
        "course": course,
        "header": header,
        "column": column,
    }

# {% user_answers_title %}
@register.filter
def user_answers_title(course):
    return course.name if course else SUMMARY_TITLE

# {% heading_id %}
@register.filter
def heading_id(course):
    return "data-" + (course.slug + "-course" if course else SUMMARY_ID)

# {% table_id %}
@register.filter
def table_id(course):
    return "table-" + (course.slug if course else SUMMARY_ID)
        
        
