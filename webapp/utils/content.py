import re
from collections import defaultdict

import courses.models as cm
from django.utils.text import slugify as slugify
from reversion.models import Version, Revision

def first_title_from_content(content_text):
    """
    Finds the first heading from a content page and returns the title. Also
    returns the slugified anchor.
    """

    titlepat = re.compile("(?P<level>={1,6}) ?(?P<title>.*) ?(?P=level)")
    try:
        title = titlepat.search(content_text).group("title").strip()
    except AttributeError:
        title = ""
        anchor = ""
    else:
        anchor = slugify(title, allow_unicode=True)

    return title, anchor

def get_course_instance_tasks(instance, deadline_before=None):
    """
    Goes through all the content links in the given course instance to compile
    a list of tasks in the instance, grouped by content page. The tasks are
    returned as a list of tuples where
    # first item is the parent page object
    # second item is the embedded task object
    
    If deadline_before (DateTime) is set, will only include tasks from pages
    that had a deadline before the given date.
    """

    all_embedded_links = cm.EmbeddedLink.objects.filter(instance=instance).order_by("embedded_page__name").select_related("embedded_page")

    task_pages = []

    content_links = cm.ContentGraph.objects.filter(instance=instance, scored=True, visible=True).order_by("ordinal_number").select_related("content")
    if deadline_before is not None:
        content_links = content_links.filter(deadline__lt=deadline_before)

    for content_link in content_links:
        page_task_links = all_embedded_links.filter(parent=content_link.content)
        if page_task_links:
            task_pages.append((content_link.content, page_task_links))

    return task_pages

def get_embedded_parent(content, instance):
    """
    Gets the embedded parent of a content object. Returns two values: the
    parent content object or None, and boolean value that tells whether there
    was a parent or not.
    """
    
    try:
        link = cm.EmbeddedLink.objects.get(embedded_page=content, instance=instance)
    except cm.EmbeddedLink.MultipleObjectsReturned:
        return None, False
    else:
        return link.parent, True
    

# Modified from reversion.models.Revision.revert
# NOTE: Outdated, functions in utils.archive should be used.
def get_archived_instances(main_obj, revision_id):
    revision = Revision.objects.get(id=revision_id)
    archived_objects = set()
    for version in revision.version_set.iterator():
        model = version._model
        try:
            archived_objects.add(
                model._default_manager.using(version.db).get(pk=version.object_id)
            )
        except model.DoesNotExist:
            pass
        
    by_model = defaultdict(list)
    for obj in archived_objects:
        by_model[obj.__class__.__name__].append(obj)
        
    return by_model

    
# NOTE: Outdated, functions in utils.archive should be used.
def get_instance_revision(model_class, instance_id, revision):
    instance_obj = model_class.objects.get(id=instance_id)
    if revision is not None:
        return Version.objects.get_for_object(instance_obj).get(revision=revision)._object_version.object
    return instance_obj

def get_parent_context(exercise, instance):
    return ContentGraph.objects.filter(
        content__embdedded_pages=exercise, instance=instance
    ).distinct("id").first()


def compile_json_feedback(log):
    # render all individual messages in the log tree
    triggers = []
    hints = []

    for test in log:
        test["title"] = "".join(markupparser.MarkupParser.parse(test["title"], request, context)).strip()
        test["runs"].sort(key=lambda run: run["correct"])
        for run in test["runs"]:
            for output in run["output"]:
                output["msg"] = "".join(markupparser.MarkupParser.parse(output["msg"], request, context)).strip()
                triggers.extend(output.get("triggers", []))
                hints.extend(
                    "".join(markupparser.MarkupParser.parse(msg, request, context)).strip()
                    for msg in output.get("hints", [])
                )

    t_messages = loader.get_template('courses/exercise-evaluation-messages.html')
    feedback = {
        'messages': t_messages.render({'log': log}),
        'hints': hints,
        'triggers': triggers
    }
    return feedback

def get_embedded_media_file(name, instance, parent):
    """
    Gets an embedded media file within a given instance context. Will return
    either the current version, or the revision specified in the media link.
    Will accept None as instance or parent. In these cases the current version
    will always be returned.
    """

    try:
        link = cm.CourseMediaLink.objects.get(
            media__name=name,
            instance=instance,
            parent=parent
        )
    except (KeyError, cm.CourseMediaLink.DoesNotExist) as e:
        file_object = cm.File.objects.get(name=name)
    else:
        if link.revision is None:
            file_object = link.media.file
        else:
            revision_object = Version.objects.get_for_object(link.media.file).get(revision=link.revision)
            file_object = revision_object._object_version.object
            
            # is there a better way to get parent attributes
            # from the version object?
            file_object.name = revision_object.field_dict["name"]
    return file_object
    
def get_embedded_media_image(name, instance, parent):
    """
    Gets an embedded media image within a given instance context. Will return
    either the current version, or the revision specified in the media link.
    Will accept None as instance or parent. In these cases the current version
    will always be returned.
    """

    try:
        link = cm.CourseMediaLink.objects.get(
            media__name=name,
            instance=instance,
            parent=parent
        )
    except (KeyError, cm.CourseMediaLink.DoesNotExist) as e:
        image_object = cm.Image.objects.get(name=name)
    else:
        if link.revision is None:
            image_object = link.media.image
        else:
            revision_object = Version.objects.get_for_object(link.media.image).get(revision=link.revision)
            image_object = revision_object._object_version.object
            
            # is there a better way to get parent attributes
            # from the version object?
            image_object.name = revision_object.field_dict["name"]
    return image_object
