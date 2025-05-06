from django import template
register = template.Library()

#https://stackoverflow.com/questions/2152250/how-to-set-tabindex-on-forms-fields
@register.filter
def tabindex_attr(value):
    """
    Add a tabindex attribute to the widget for a bound field.
    """

    value.field.widget.attrs['tabindex'] = 0
    return value



