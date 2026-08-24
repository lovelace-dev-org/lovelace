from django.forms.fields import ChoiceField
from courses.widgets import OriginFilterSelect
from utils.access import accessible_courses

class OriginFilterField(ChoiceField):
    """
    Field class for choosing content filtered by origin. This field validates
    its selected value by checking the selected model instance's origin against
    the provided list of courses.
    """


    widget = OriginFilterSelect

    def to_python(self, value):
        if value:
            inst = self._model.objects.get(id=value)
        else:
            return None
        return inst

    def valid_value(self, value):
        if value:
            return value.origin in self._access_list
        return value is None

    def __init__(self, *, choices=(), **kwargs):
        self._model = kwargs.pop("model")
        self._access_list = kwargs.pop("access_list")
        super().__init__(choices=choices, **kwargs)

