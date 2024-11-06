import itertools
import json
import logging
import math
import os
import shutil
import uuid
from collections import defaultdict
from decimal import Decimal
from datetime import date, datetime
from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.utils.translation import gettext as _
from modeltranslation.translator import translator, NotRegistered
from reversion import revisions as reversion
from lovelace import plugins as lovelace_plugins
import courses.models as cm

logger = logging.getLogger(__name__)

def field_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, Decimal):
        return str(obj)

    if isinstance(obj, uuid.UUID):
        return str(obj)

    raise TypeError ("Type %s not serializable" % type(obj))

def export_json(document, fname, target):
    if document:
        path = os.path.join(document[0]["model"], fname) + ".json"
        target.writestr(path, json.dumps(document, indent=4, default=field_serializer))

def export_files(model, target, filetype, field="fileinfo", translate=False):
    files_to_save = []
    if translate:
        files = []
        for lang_code, __ in settings.LANGUAGES:
            files.append(getattr(model, f"{field}_{lang_code}"))
    else:
        files = [getattr(model, field)]

    for fileinfo in files:
        if fileinfo:
            target.write(
                fileinfo.path.encode("utf-8"),
                os.path.join("datafiles", filetype, str(fileinfo))
            )



def deserialize_python(document):
    return serializers.deserialize(
        "python", document,
        ignorenonexistent=True,
        use_natural_foreign_keys=True,
        use_natural_primary_keys=True,
        handle_forward_references=True,
    )

def serialize_single_python(model_inst):
    return serializers.serialize(
        "python", [model_inst],
        use_natural_foreign_keys=True,
        use_natural_primary_keys=True
    )

def serialize_many_python(queryset):
    return serializers.serialize(
        "python", queryset,
        use_natural_foreign_keys=True,
        use_natural_primary_keys=True
    )


def import_allowed(obj, user, instance):
    #model_class = obj.object.__class__

    #try:
    #    existing = model_class.objects.get_by_natural_key(*obj.object.natural_key())
    #except model_class.DoesNotExist:
    #    return True

    return True

def fix_default_lang_fields(obj):
    """
    Fixes default language fields when importing content from an instance with a different
    default language setting. The process takes the value from the first fallback field
    that has content and moves it to the default language field if the default language field
    is empty.

    The current solution will result in weird behavior if there are multiple filled fields
    but the default is empty.
    """

    model = obj.__class__
    try:
        translated = translator.get_options_for_model(model).get_field_names()
    except NotRegistered:
        return

    languages = settings.LANGUAGES
    default = settings.MODELTRANSLATION_DEFAULT_LANGUAGE
    fallbacks = settings.MODELTRANSLATION_FALLBACK_LANGUAGES[1:]
    for field in translated:
        default_value =  getattr(obj, f"{field}_{default}")
        if not default_value:
            for lang_code in fallbacks:
                value = getattr(obj, f"{field}_{lang_code}")
                if value:
                    setattr(obj, f"{field}_{default}", value)
                    setattr(obj, f"{field}_{lang_code}", default_value)
                    break

def import_from_zip(import_source, user, responsible, staff_group, target_instance=None):
    deferred = []
    errors = []

    model_list = cm.get_import_list()
    for module in lovelace_plugins["import"]:
        model_list.extend(module.models.get_import_list())

    model_names = [
        f"{model._meta.app_label}.{model._meta.model_name}" for model in model_list
    ]

    def _sorter(item):
        first, _ = item.split("/", 1)
        if first == "courses.course":
            return (0, item)
        if first == "courses.courseinstance":
            return (1, item)
        if first == "datafiles":
            return (2, item)
        return (model_names.index(first) + 3, item)

    def _grouper(item):
        return item.split("/", 1)[0]

    # target_course and target_instance are not currently used but left
    # here in case support for importing into different course/instance
    # will be revisited in the future
    def import_model(source_doc, target_course=None, target_instance=None):
        imported = []

        for serialized_dict in source_doc:
            if "pk" in serialized_dict:
                logger.error(f"Serialized data contains pk, importing aborted.")
                raise ValueError("Imported data is not allowed to define pk")

        with reversion.create_revision():
            for obj in deserialize_python(source_doc):
                if not import_allowed(obj, user, target_instance):
                    errors.append(_("Import of {obj_str} failed - no overwrite permission").format(
                        obj_str=str(obj.object)
                    ))
                    continue

                fix_default_lang_fields(obj.object)
                obj.save()
                imported.append(obj.object)
                if obj.deferred_fields is not None:
                    deferred.append(obj)
            reversion.set_comment("imported by system")

        return imported


    names = import_source.namelist()
    names.sort(key=_sorter)

    imported_course_doc = json.loads(import_source.read(names.pop(0)))
    imported_instance_doc = json.loads(import_source.read(names.pop(0)))
    if target_instance is None:
        imported_course_doc[0]["fields"]["staff_group"] = staff_group.natural_key()
        imported_course_doc[0]["fields"]["main_responsible"] = responsible.natural_key()
        course = import_model(imported_course_doc)[0]
        instance = import_model(imported_instance_doc, course)[0]
    else:
        if target_instance.slug != imported_instance_doc[0]["fields"]["slug"]:
            raise ValueError(_(
                "Content updates can only be imported to an instance with the same name "
                "as the original"
            ))

        if list(target_instance.course.natural_key()) != imported_instance_doc[0]["fields"]["course"]:
            raise ValueError(_(
                "Content updates can only be imported to an instance of the same course "
                "as the original"
            ))

        course = target_instance.course
        instance = target_instance

    imported_course_name = instance.course.name

    for block_type, group in itertools.groupby(names, _grouper):
        if block_type == "datafiles":
            for name in group:
                storage = name.split("/")[1]
                if storage == "media":
                    root = settings.MEDIA_ROOT
                else:
                    root = settings.PRIVATE_STORAGE_FS_PATH
                path = os.path.join(root, *name.split("/")[2:])
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as target:
                    target.write(import_source.read(name))
        else:
            for name in group:
                try:
                    import_model(json.loads(import_source.read(name)), course, instance)
                except Exception as e:
                    logger.warning(f"Error while handling file {name} under model {block_type}")
                    raise e

    for obj in deferred:
        obj.save_deferred_fields()

    return instance, errors
