import itertools
import json
import logging
import math
import os
import shutil
import time
import uuid
from collections import defaultdict
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.apps import apps
from django.conf import settings
from django.contrib.admin.utils import NestedObjects
from django.core import serializers
from django.db import router
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

            # Change origin to the current course
            # when importing objects that had different origins
            if origin := serialized_dict["fields"].get("origin"):
                if origin != target_course.natural_key():
                    print("Setting origin to:", target_course.natural_key())
                    serialized_dict["fields"]["origin"] = target_course.natural_key()


            for obj in deserialize_python(source_doc):
                if not import_allowed(obj, user, target_instance):
                    errors.append(_("Import of {obj_str} failed - no overwrite permission").format(
                        obj_str=str(obj.object)
                    ))
                    continue

                fix_default_lang_fields(obj.object)

                try:
                    obj.save()
                except Exception as e:
                    errors.append(_("Import of {obj_str} failed - missing dependencies").format(
                        obj_str=str(obj.object)
                    ))
                    continue

                imported.append(obj.object)
                if obj.deferred_fields is not None:
                    deferred.append(obj)

        return imported


    names = import_source.namelist()
    names.sort(key=_sorter)

    imported_course_doc = json.loads(import_source.read(names.pop(0)))
    imported_instance_doc = json.loads(import_source.read(names.pop(0)))
    if target_instance is None:
        imported_course_doc[0]["fields"]["staff_group"] = staff_group.natural_key()
        imported_course_doc[0]["fields"]["main_responsible"] = responsible.natural_key()
        print(f"Importing course")
        course = import_model(imported_course_doc)[0]
        print(f"Importing course instance")
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

    with reversion.create_revision():

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
                    print(f"Importing {block_type} {name}")
                    try:
                        import_model(json.loads(import_source.read(name)), course, instance)
                    except Exception as e:
                        logger.warning(f"Error while handling file {name} under model {block_type}")
                        raise e

        for obj in deferred:
            try:
                obj.save_deferred_fields()
            except serializers.base.DeserializationError:
                logger.warning(f"Cannot save deferred fields for {obj}")
                errors.append(_("Import of deferred fields failed for {obj_str}").format(
                    obj_str=str(obj.object)
                ))
        reversion.set_comment("imported by system")

    return instance, errors

def apply_data_retention(preview=True, show_progress=False):
    """
    Function for applying data retention policy settings. Checks through all course instances where
    the end date is older than the server's data retention time setting. User data retention policy
    affects data handling as follows:
    1) Retain policy
        - Only calendar reservations are deleted, everything else is kept as is.
    2) Delete policy
        - A generated "deleted-user" replaces the user to maintain a record that a user who was
          enrolled has been deleted.
        - All data the user has in the course instance is deleted.
    3) Anonymize policy
        - A generated "generated-user" takes ownership of all the user's data in the course instance
        - Calendar reservations are deleted

    All models that have been registered to courses.models.UserProfile as containing user data are
    affected.

    This function returns a dictionary that shows number of changes made or changes that will
    be made if run in preview mode.
    """

    retention_threshold = (
        datetime.now() - timedelta(weeks=settings.DATA_RETENTION_PERIOD * 4)
    )

    # Delete or anonymize answer and completion related data based on user's chosen data policy
    ended_course_instances = cm.CourseInstance.objects.filter(end_date__lt=retention_threshold)

    affected = defaultdict(dict)

    if show_progress:
        print("Starting delete / anonymize process")
        if preview:
            print("in PREVIEW mode")
        else:
            print("in EXECUTION mode")
            time.sleep(2)

    for instance in ended_course_instances:
        if show_progress:
            print(
                f"Processing course instance: {instance.course.name} - {instance.name}"
                f" (ended {instance.end_date.isoformat()}"
            )

        # Users without profile (i.e. generated users) will not be included in these filters
        enrolled_users = instance.enrolled_users.get_queryset()
        delete_setting = list(enrolled_users.filter(userprofile__data_policy="DELETE"))
        anonymize_setting = list(enrolled_users.filter(userprofile__data_policy="ANONYMIZE"))

        # Move enrollments of deleted users to "deleted user" dummies to retain participation numbers
        if not preview:
            if show_progress:
                print("Creating deleted-user accounts.")

            total = len(delete_setting)
            for i, user in enumerate(delete_setting, start=1):
                if show_progress:
                    print(f"{i} / {total}\r", end="", flush=True)

                deleted_anon = cm.User(
                    username=f"deleted-user-{str(uuid.uuid1())}"
                )
                deleted_anon.save()
                count = cm.CourseEnrollment.objects.filter(
                    student=user, instance=instance
                ).update(student=deleted_anon)
                try:
                    affected[cm.CourseEnrollment._meta.label]["deleted"] += count
                except KeyError:
                    affected[cm.CourseEnrollment._meta.label]["deleted"] = count

            if show_progress:
                print()

        # Delete everything else that belongs to users with a delete policy
        for model_cls, fields in cm.UserProfile.user_data_models:
            if show_progress:
                print(f"Deleting {model_cls._meta.label} instances")

            for field in fields:
                if show_progress:
                    print(f"Deleting via field: {field}")

                queryset = model_cls.objects.filter(
                    **{f"{field}__in": delete_setting, "instance": instance}
                )
                if preview:
                    deleted_objects = list(queryset)
                    try:
                        affected[model_cls._meta.label]["deleted"] += deleted_objects
                    except KeyError:
                        affected[model_cls._meta.label]["deleted"] = deleted_objects
                    count = len(deleted_objects)
                else:
                    count = queryset.delete()
                    try:
                        affected[model_cls._meta.label]["deleted"] += count
                    except KeyError:
                        affected[model_cls._meta.label]["deleted"] = count

                if show_progress:
                    print(f"Objects deleted: {count}")
                    print()

        # Create an anonymous clone for each user with anonymize policy and transfer everything
        # to it
        total = len(anonymize_setting)
        for user in anonymize_setting:
            if show_progress:
                print("Anonymizing users.")

            if show_progress:
                print(f"{i} / {total}\r", end="", flush=True)

            if not preview:
                new_anon = cm.User(
                    username=f"generated-user-{str(uuid.uuid1())}"
                )
                new_anon.save()

            for model_cls, fields in cm.UserProfile.user_data_models:
                for field in fields:
                    queryset = model_cls.objects.filter(**{field: user, "instance": instance})
                    if preview:
                        try:
                            affected[model_cls._meta.label]["anonymized"] += list(queryset)
                        except KeyError:
                            affected[model_cls._meta.label]["anonymized"] = list(queryset)
                    else:
                        count = queryset.update(**{field: new_anon})
                        try:
                            affected[model_cls._meta.label]["anonymized"] += count
                        except KeyError:
                            affected[model_cls._meta.label]["anonymized"] = count

            if show_progress:
                print()


    # Delete all old calendar reservations regardless of user data policy
    if show_progress:
        print("Deleting calendar reservations")

    queryset = cm.CalendarReservation.objects.filter(calendar_date__end_time__lt=retention_threshold)
    if preview:
        deleted_objects = list(queryset)
        affected[cm.CalendarReservation._meta.label]["deleted"] = deleted_objects
        count = len(deleted_objects)
    else:
        count = queryset.delete()

    if show_progress:
        print(f"Deleted {count} calendar reservations")
        print()

    # Delete all users whose policy is delete or anonymize if their last login is older than
    # data retention period
    if show_progress:
        print("Deleting users")

    # Account for session age
    login_threshold = (
        retention_threshold - timedelta(seconds=settings.ACCOUNT_SESSION_COOKIE_AGE)
    )
    non_retain_setting = cm.User.objects.filter(
        userprofile__data_policy__in=["DELETE", "ANONYMIZE"],
        last_login__lt=login_threshold
    )
    if preview:
        deleted_objects = list(non_retain_setting)
        affected[cm.User._meta.label]["deleted"] = deleted_objects
        count = len(deleted_objects)
    else:
        count = non_retain_setting.delete()
        affected[cm.User._meta.label]["deleted"] = count

    if show_progress:
        print(f"Deleted {count} users")

    return affected
