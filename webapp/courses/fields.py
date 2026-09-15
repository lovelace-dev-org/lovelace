from django.forms.fields import ChoiceField, MultipleChoiceField
from django.forms.models import ModelMultipleChoiceField
from courses.widgets import OriginFilterSelect, OriginFilterMultiSelect
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


class OriginFilterMultiField(MultipleChoiceField):

    widget = OriginFilterMultiSelect

    def to_python(self, value):
        if not value:
            return []
        return [self._model.objects.get(id=item_id) for item_id in value]

    def valid_value(self, value):
        return value.origin in self._access_list

    def __init__(self, *, choices=(), **kwargs):
        self._model = kwargs.pop("model")
        self._access_list = kwargs.pop("access_list")
        super().__init__(choices=choices, **kwargs)


class ModelOriginFilterMultiField(ModelMultipleChoiceField):
    """
    Modelform compatible version of OriginFilterMultiField.
    """

    widget = OriginFilterMultiSelect

    def valid_value(self, value):
        return (
            self._model.objects.filter(id=value).only("origin").first().origin in self._access_list
        )

    def __init__(self, *, queryset=None, **kwargs):
        self._model = kwargs.pop("model")
        self._access_list = kwargs.pop("access_list")
        super().__init__(queryset=queryset, **kwargs)
