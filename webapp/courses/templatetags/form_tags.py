from django import template
register = template.Library()

global_index = 0

#https://stackoverflow.com/questions/2152250/how-to-set-tabindex-on-forms-fields
@register.filter
def tabindex_attr(value):
    """
    Add a tabindex attribute to the widget for a bound field.
    """

    global global_index
    global_index += 1
    value.field.widget.attrs['tabindex'] = global_index
    return value

@register.simple_tag
def tabindex_value():
    global global_index
    global_index += 1
    return global_index


