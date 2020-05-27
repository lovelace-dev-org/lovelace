from collections import defaultdict
from django.db import transaction
from reversion.models import Version, Revision
from reversion import revisions

class CancelRevert(Exception):
    """
    An exception used to cause a rollback after reading data from the
    reverted database state.
    """
    
    pass

# TODO: add support to use prefetch_related on followed sets.    
def get_archived_instances(main_obj, revision_id):
    """
    Gets archived instances of a model and any models listed in its follow
    options. This approach is modeled after how reversion's version history
    admin fetches history information: it reverts the database to a given
    revision, reads all the model instances into memory, and finally causes a
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
                by_model[field] = list(getattr(main_obj, field).get_queryset().all())
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

    return Version.objects.get_for_object(model_instance)\
        .get(revision=revision_id)\
        ._object_version.object
