from django.forms.fields import ChoiceField
from courses.widgets import OriginFilterSelect

class OriginFilterField(ChoiceField):
    """
    Field class for choosing content filtered by origin. This field validates
    its selected value by using an origin validator which needs to be provided by
    the form since this field class does not know the model class it's validating origin
    for nor does it know the user it's validating access for.
    """

    widget = OriginFilterSelect

    def valid_value(self, value):
        return self._origin_validator(value)

    def __init__(self, *, choices=(), **kwargs):
        self._origin_validator = kwargs.pop("origin_validator")
        super().__init__(choices=choices, **kwargs)


