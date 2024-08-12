import datetime
import re
from collections import defaultdict
from functools import wraps
import django.conf
from django.http import HttpResponseNotFound
from django.template import engines, loader
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from reversion.models import Version, Revision
from courses import markupparser
import courses.models as cm
from utils.access import is_course_staff
from utils.exercise import best_result


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

def _parent_ordinal_sort(pair):
    node = pair[0]
    ordinals = [node.ordinal_number]
    parent_node = node.parentnode
    while parent_node is not None:
        ordinals.insert(0, parent_node.ordinal_number)
        parent_node = parent_node.parentnode
    return ordinals


def get_answer_count_meta(answer_count):
    t = engines["django"].from_string(
        "{% load i18n %}{% blocktrans count counter=answer_count %}<span class='answer-count'>"
        "{{ counter }}</span> answer{% plural %}<span class='answer-count'>{{ counter }}</span>"
        " answers{% endblocktrans %}"
    )
    return t.render({"answer_count": answer_count})


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

    all_embedded_links = (
        cm.EmbeddedLink.objects.filter(instance=instance)
        .order_by("embedded_page__name")
        .select_related("embedded_page")
        .defer("embedded_page__content")
    )

    task_pages = []

    content_links = (
        cm.ContentGraph.objects.filter(instance=instance, scored=True, visible=True)
        .order_by("ordinal_number")
        .select_related("content")
        .defer("content__content")
    )

    if deadline_before is not None:
        content_links = content_links.filter(deadline__lt=deadline_before)

    for content_link in content_links:
        page_task_links = all_embedded_links.filter(parent=content_link.content)
        if page_task_links:
            task_pages.append((content_link, page_task_links))

    task_pages.sort(key=_parent_ordinal_sort)
    return task_pages


def regenerate_nearest_cache(content):
    """
    Executes a cache regen for content. As caching is done by actual page, this means either
    regenerating cache of the content itself if it is a top-level page, or its embed parent if
    it's an embedded page.
    """

    for cg in cm.ContentGraph.objects.filter(content=content, revision=None):
        content.regenerate_cache(cg.instance, active_only=True)
    else:
        for embed in cm.EmbeddedLink.objects.filter(embedded_page=content):
            embed.parent.regenerate_cache(embed.instance, active_only=True)


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
            archived_objects.add(model._default_manager.using(version.db).get(pk=version.object_id))
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
        return (
            Version.objects.get_for_object(instance_obj)
            .get(revision=revision)
            ._object_version.object
        )
    return instance_obj


def get_parent_context(exercise, instance):
    return (
        cm.ContentGraph.objects.filter(content__embdedded_pages=exercise, instance=instance)
        .distinct("id")
        .first()
    )


def get_embedded_media_file(name, instance, parent):
    """
    Gets an embedded media file within a given instance context. Will return
    either the current version, or the revision specified in the media link.
    Will accept None as instance or parent. In these cases the current version
    will always be returned.
    """

    try:
        link = cm.CourseMediaLink.objects.get(media__name=name, instance=instance, parent=parent)
    except (KeyError, cm.CourseMediaLink.DoesNotExist) as e:
        file_object = cm.File.objects.get(name=name)
    else:
        if link.revision is None:
            file_object = link.media.file
        else:
            revision_object = Version.objects.get_for_object(link.media.file).get(
                revision=link.revision
            )
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
        link = cm.CourseMediaLink.objects.get(media__name=name, instance=instance, parent=parent)
    except (KeyError, cm.CourseMediaLink.DoesNotExist) as e:
        image_object = cm.Image.objects.get(name=name)
    else:
        if link.revision is None:
            image_object = link.media.image
        else:
            revision_object = Version.objects.get_for_object(link.media.image).get(
                revision=link.revision
            )
            image_object = revision_object._object_version.object

            # is there a better way to get parent attributes
            # from the version object?
            image_object.name = revision_object.field_dict["name"]
    return image_object


def cookie_law(view_func):
    """
    To comply with the European Union cookie law, display a warning about the
    site using cookies. When the user accepts cookies, set a session variable to
    disable the message.
    """

    @wraps(view_func)
    def func_wrapper(request, *args, **kwargs):
        if "cookies_accepted" in request.COOKIES:
            if request.COOKIES["cookies_accepted"] == "1":
                request.session["cookies_accepted"] = True
        if request.session.get("cookies_accepted"):
            pass
        else:
            request.session["cookies_accepted"] = False
        return view_func(request, *args, **kwargs)

    return func_wrapper


def check_exercise_accessible(request, course, instance, content):
    embedded_links = cm.EmbeddedLink.objects.filter(embedded_page_id=content.id, instance=instance)
    content_graph_links = cm.ContentGraph.objects.filter(instance=instance, content=content)

    if content_graph_links.first() is None and embedded_links.first() is None:
        return {
            "error": HttpResponseNotFound(
                f"Content {content.slug} is not linked to course {course.slug}!"
            )
        }

    return {
        "embedded_links": embedded_links,
        "content_graph_links": content_graph_links,
        "error": None,
    }


def course_tree(tree, node, user, instance_obj, enrolled=False, staff=False):
    if node.require_enroll:
        if not (enrolled or staff):
            return

    embedded_links = (
        cm.EmbeddedLink.objects.filter(parent=node.content.id, instance=instance_obj)
    )
    embedded_count = embedded_links.count()
    page_count = node.content.count_pages(instance_obj)

    correct_embedded = 0
    page_score = 0
    page_max = 0

    evaluation = ""
    if user.is_authenticated:
        exercise = node.content
        evaluation = exercise.get_user_evaluation(user, instance_obj)

        if embedded_count > 0:
            grouped = embedded_links.exclude(embedded_page__evaluation_group="")
            group_tags = (
                grouped.order_by("embedded_page__evaluation_group")
                .distinct("embedded_page__evaluation_group")
                .values_list("embedded_page__evaluation_group", flat=True)
            )

            embedded_count -= grouped.count() - len(group_tags)

            for tag in group_tags:
                group_score, representative = best_result(user, instance_obj, tag)
                if group_score > -1:
                    correct_embedded += 1
                    if not grouped.filter(embedded_page=representative).exists():
                        continue
                    page_score += group_score * representative.default_points * node.score_weight
                page_max += representative.default_points * node.score_weight

            for emb_link in embedded_links.filter(embedded_page__evaluation_group=""):
                emb_exercise = emb_link.embedded_page
                correct, score = emb_exercise.get_user_evaluation(user, instance_obj)
                page_max += emb_exercise.default_points * node.score_weight
                if correct == "correct":
                    correct_embedded += 1
                    page_score += score * emb_exercise.default_points * node.score_weight

    deadline = node.deadline
    if user.is_authenticated:
        exemption = cm.DeadlineExemption.objects.filter(
            user=user,
            contentgraph=node
        ).first()
        if exemption:
            deadline = exemption.new_deadline

    list_item = {
        "node_id": node.id,
        "content": node.content,
        "evaluation": evaluation,
        "correct_embedded": correct_embedded,
        "embedded_count": embedded_count,
        "page_score": f"{page_score:.2f}",
        "page_max": f"{page_max:.2f}",
        "visible": node.visible,
        "require_enroll": node.require_enroll,
        "page_count": page_count,
        "deadline": deadline,
        "urgency": get_deadline_urgency(deadline),
    }

    if list_item not in tree:
        tree.append(list_item)

    if is_course_staff(user, instance_obj):
        children = cm.ContentGraph.objects.filter(parentnode=node, instance=instance_obj).order_by(
            "ordinal_number"
        )
    else:
        children = cm.ContentGraph.objects.filter(
            parentnode=node, instance=instance_obj, visible=True
        ).order_by("ordinal_number")

    if len(children) > 0:
        tree.append({"content": mark_safe(">")})
        for child in children:
            course_tree(tree, child, user, instance_obj, enrolled, staff)
        tree.append({"content": mark_safe("<")})


