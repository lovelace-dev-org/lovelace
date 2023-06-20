import datetime
import os.path
from collections import defaultdict
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models.query import QuerySet
from reversion.models import Version
from reversion import revisions


class CancelRevert(Exception):
    """
    An exception used to cause a rollback after reading data from the
    reverted database state.
    """


# TODO: add support to use prefetch_related on followed sets.
def get_archived_instances(main_obj, revision_id):
    """
    Gets archived instances of a model and any models listed in its follow
    options. This approach is modeled after how reversion's version history
    admin fetches history information: it reverts the database to a given
    revision, reads all there model instances into memory, and finally causes a
    rollback to restore the database to the most recent state.

    Returns a dictionary that contains each related set as a list (using the
    set's attribute name as the key), and the archived version of the parent
    object (using "self" as the key)
    """

    by_model = defaultdict(list)
    version = Version.objects.get_for_object(main_obj).get(revision=revision_id)
    try:
        with transaction.atomic(using=version.db):
            version.revision.revert(delete=True)
            by_model["self"] = version._object_version.object
            follow = revisions._get_options(main_obj).follow
            for field in follow:
                try:
                    follow_obj = getattr(main_obj, field)
                except ObjectDoesNotExist:
                    by_model[field] = None
                    continue
                if isinstance(follow_obj, models.Model):
                    by_model[field] = follow_obj
                elif isinstance(follow_obj, (models.Manager, QuerySet)):
                    by_model[field] = list(follow_obj.get_queryset().all())
            raise CancelRevert
    except CancelRevert:
        pass

    return by_model


def get_archived_field(main_obj, revision_id, field):
    """
    Convenience function to get archived contents for one field. The field can
    be any _set attribute from the parent object's follow options, or "self" to
    get archived copy of the object itself.
    """

    archive_copy = get_archived_instances(main_obj, revision_id)
    return archive_copy[field]


def get_single_archived(model_instance, revision_id):
    """
    Gets an archived instance of a model instance without doing a
    revert-rollback on the database. Please note that this does not revert
    relationships! Referencing to other models through any relationship type
    attributes in the returned object will refer to most recent set of related
    models. If you need archived version of related objects listing, please use
    get_archived_instances or get_archived_field.
    """

    try:
        return (
            Version.objects.get_for_object(model_instance)
            .get(revision=revision_id)
            ._object_version.object
        )
    except Version.DoesNotExist:
        return model_instance


def find_version_with_filename(model_instance, field, name):
    """
    Finds a version object where the (fileinfo) field had a specific filename.
    Usually used to determine if there ever was a version where the field had
    the given value.
    """

    for version in Version.objects.get_for_object(model_instance):
        if os.path.basename(version.field_dict[field].name) == name:
            return version
    return None


def find_latest_version(model_instance, before=None):
    """
    Finds the latest version object for the given model instance. If the
    optional before (DateTime instance) parameter is set, the returned
    version will be the latest revision that is dated before the given time.
    """

    versions = Version.objects.get_for_object(model_instance)
    if before:
        versions = versions.filter(revision__date_created__lte=before)
    return versions.latest("revision__date_created")


def squash_revisions(model_instance, hours):
    """
    Finds versions of model_instance that are not older than given number of hours
    and deletes all but the latest of them. Use this in tools that are likely to create
    a lot of revisions when content is being edited.
    """

    now = datetime.datetime.now()
    span = datetime.timedelta(hours=hours)
    versions = Version.objects.get_for_object(model_instance)
    latest = versions.latest("revision__date_created")
    versions.filter(revision__date_created__gte=now-span).exclude(id=latest.id).delete()


