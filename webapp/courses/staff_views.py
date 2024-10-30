from html import escape
import json
import os
import tempfile
import zipfile

from django.conf import settings
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseNotFound,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseBadRequest,
)
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from reversion import revisions as reversion

from courses import blockparser
from courses import markupparser
import courses.models as cm
from courses.models import (
    CourseInstance,
    ContentGraph,
    ContentPage,
    EmbeddedLink,
    Lecture,
    StudentGroup,
    Term,
    User,
)
from courses.forms import (
    CacheRegenForm,
    GroupForm,
    GroupMemberForm,
    InstanceCloneForm,
    InstanceExportForm,
    InstanceFreezeForm,
    InstanceImportForm,
    InstanceGradingForm,
    InstanceSettingsForm,
    NewContentNodeForm,
    NodeSettingsForm,
)
from courses.edit_forms import (
    get_form,
    save_form,
    place_into_content,
    BlockTypeSelectForm,
    TermifyForm,
)
from utils.access import (
    determine_media_access,
    ensure_responsible_or_supervisor,
    ensure_responsible,
    ensure_staff,
)
from utils.archive import find_latest_version, squash_revisions
from utils.content import regenerate_nearest_cache
from utils.data import field_serializer, import_from_zip
from utils.management import (
    CourseContentAdmin,
    clone_instance_files,
    clone_terms,
    clone_content_graphs,
    clone_grades,
)
from faq.utils import clone_faq_links
from assessment.utils import clone_assessment_links

from lovelace import plugins as lovelace_plugins

# INSTANCE MANAGEMENT VIEWS
# |
# v

@ensure_staff
def instance_settings(request, course, instance):
    content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
    available_content = content_access.defer("content").all()

    if request.method == "POST":
        form = InstanceSettingsForm(
            request.POST, instance=instance, available_content=available_content
        )
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        instance = form.save(commit=False)
        try:
            frontpage = ContentPage.objects.get(id=form.cleaned_data["frontpage"])
        except ContentPage.DoesNotExist:
            instance.save()
            return JsonResponse({"status": "ok"})

        fp_node = ContentGraph.objects.filter(instance=instance, ordinal_number=0).first()
        if fp_node:
            fp_node.content = frontpage
            fp_node.save()
        else:
            fp_node = ContentGraph(
                content=frontpage, instance=instance, scored=False, ordinal_number=0
            )
            fp_node.save()
        fp_node.content.update_embedded_links(instance, fp_node.revision)
        ContentGraph.objects.filter(content=frontpage, ordinal_number__gt=0).delete()
        instance.frontpage = frontpage
        instance.save()
        return JsonResponse({
            "status": "ok",
            "redirect": reverse(
                "courses:course", kwargs={"course": course, "instance": instance}
            )
        })

    form = InstanceSettingsForm(
        instance=instance,
        available_content=available_content,
        initial={"frontpage": instance.frontpage and instance.frontpage.id},
    )
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "courses:instance_settings", kwargs={"course": course, "instance": instance}
        ),
        "html_id": "instance-settings-form",
        "html_class": "toc-form staff-only",
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def freeze_instance(request, course, instance):
    if request.method == "POST":
        form = InstanceFreezeForm(
            request.POST,
        )
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        instance.freeze(freeze_to=form.cleaned_data["freeze_to"])
        instance.save()
        return JsonResponse({"status": "ok"})

    form = InstanceFreezeForm()
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "courses:freeze_instance", kwargs={"course": course, "instance": instance}
        ),
        "html_id": "instance-freeze-form",
        "html_class": "toc-form staff-only",
        "disclaimer": _(
            "Freeze this instance to reflect its state at the given date. "
            "This operation is not intended to be reversible."
        ),
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def clone_instance(request, course, instance):
    if request.method == "POST":
        old_pk = instance.id
        form = InstanceCloneForm(request.POST, instance=instance)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        new_instance = form.save(commit=False)
        new_instance.pk = None
        new_instance.primary = False
        for lang_code, __ in settings.LANGUAGES:
            field = f"name_{lang_code}"
            setattr(new_instance, field, form.cleaned_data[field])
        new_instance.save()
        new_instance.refresh_from_db()
        old_instance = CourseInstance.objects.get(id=old_pk)
        clone_content_graphs(old_instance, new_instance)
        clone_grades(old_instance, new_instance)
        clone_instance_files(new_instance)
        clone_terms(new_instance)
        clone_faq_links(new_instance)
        clone_assessment_links(old_instance, new_instance)
        old_instance.clear_content_tree_cache(regen_frozen=True)
        new_url = reverse("courses:course", kwargs={"course": course, "instance": new_instance})
        return JsonResponse({"status": "ok"})

    initial_names = {}
    for lang_code, __ in settings.LANGUAGES:
        initial_names[f"name_{lang_code}"] = getattr(instance, f"name_{lang_code}")

    form = InstanceCloneForm(instance=instance, initial=initial_names)
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "courses:clone_instance", kwargs={"course": course, "instance": instance}
        ),
        "html_id": "instance-clone-form",
        "html_class": "toc-form staff-only",
        "disclaimer": _("Make a clone of this course instance."),
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def edit_grading(request, course, instance):
    if request.method == "POST":
        form = InstanceGradingForm(
            request.POST,
            instance=instance,
        )
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        form.save()
        return JsonResponse({"status": "ok"})

    form = InstanceGradingForm(
        instance=instance,
    )
    t = loader.get_template("courses/base-multi-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "courses:edit_grading", kwargs={"course": course, "instance": instance}
        ),
        "html_id": "instance-grading-form",
        "html_class": "toc-form staff-only",
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def regen_instance_cache(request, course, instance):
    if request.method == "POST":
        form = CacheRegenForm(request.POST)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        nodes = ContentGraph.objects.filter(instance=instance)
        if not form.cleaned_data["regen_archived"]:
            nodes = nodes.filter(revision=None)
        for node in nodes:
            node.content.regenerate_cache(instance)
        instance.clear_content_tree_cache()
        return JsonResponse({"status": "ok"})

    form = CacheRegenForm()
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": "instance-regenerate-form",
        "html_class": "toc-form staff-only",
        "disclaimer": _("Regenerate cache for all pages in the course. Please use sparingly."),
        "submit_label": _("Execute"),
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(form_t.render(form_c, request))


@ensure_staff
def termify(request, course, instance):
    terms = Term.objects.filter(course=course)
    if request.method == "POST":
        form = TermifyForm(request.POST, course_terms=terms)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        words_to_replace = [form.cleaned_data["baseword"]]
        if form.cleaned_data["inflections"]:
            words_to_replace.extend(form.cleaned_data["inflections"].split(","))

        replaces = []
        for word in words_to_replace:
            word = word.strip()
            replaces.append(word)

        embeds = [
            link.embedded_page for link in
            EmbeddedLink.objects.filter(instance=instance)
        ]
        pages = [
            cg.content for cg in
            ContentGraph.objects.filter(instance=instance)
        ]
        parser = markupparser.MarkupParser()
        with reversion.create_revision():
            for page in embeds + pages:
                lang = translation.get_language()
                if not getattr(page, f"content_{lang}"):
                    field = f"content_{settings.MODELTRANSLATION_DEFAULT_LANGUAGE}"
                else:
                    field = f"content_{lang}"

                termified_lines, n = parser.tag(
                    getattr(page, field),
                    form.cleaned_data["replace_in"],
                    replaces,
                    (f"[!term={form.cleaned_data['term']}!]", "[!term!]")
                )
                if n:
                    setattr(page, field, "\n".join(termified_lines))
                    page.save()
            reversion.set_user(request.user)

        for page in pages:
            regenerate_nearest_cache(page)
            squash_revisions(page, 1)

        for page in embeds:
            squash_revisions(page, 1)
        return JsonResponse({"status": "ok"})

    form = TermifyForm(course_terms=terms)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": "instance-settings-form",
        "html_class": "toc-form staff-only",
        "disclaimer": "Termify a word in all pages"
    }
    return HttpResponse(form_t.render(form_c, request))


@ensure_staff
def export_instance(request, course, instance):
    if request.method == "POST":
        form = InstanceExportForm(request.POST)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        data = []
        temp_dir_prefix = os.path.join("/", "tmp")
        with tempfile.TemporaryFile() as temp_storage:
            with zipfile.ZipFile(temp_storage, "w") as export_zip:
                instance.export(export_zip)

            temp_storage.seek(0)
            response = HttpResponse(temp_storage.read(), content_type="application/zip")
            response["Content-Disposition"] = f"attachment; filename={instance.slug}_export.zip"
            return response

    form = InstanceExportForm()
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": "toc-export-form",
        "html_class": "toc-form staff-only",
    }
    return HttpResponse(t.render(c, request))



@ensure_responsible
def import_instance(request, course, instance):
    if request.method == "POST":
        form = InstanceImportForm(request.POST, request.FILES)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        source = form.cleaned_data["import_file"]
        zf = zipfile.ZipFile(source)
        imported_instance, errors = import_from_zip(
            zf, request.user, course.main_responsible, course.staff_group,
            target_instance=instance
        )
        nodes = ContentGraph.objects.filter(instance=imported_instance, revision=None)
        for node in nodes:
            node.content.regenerate_cache(instance)

        return JsonResponse({"status": "ok", "errors": errors})

    form = InstanceImportForm()
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": "toc-export-form",
        "html_class": "toc-form staff-only",
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(t.render(c, request))


# ^
# |
# INSTANCE MANAGEMENT VIEWS
# CONTENT NODE MANAGEMENT VIEWS
# |
# v



@ensure_staff
def create_content_node(request, course, instance):
    content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
    available_content = content_access.defer("content").all()

    if request.method == "POST":
        form = NewContentNodeForm(
            request.POST,
            available_content=available_content,
            course_instance=instance
        )
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        try:
            active_node = ContentGraph.objects.get(
                instance=instance, id=form.cleaned_data["active_node"]
            )
        except ContentGraph.DoesNotExist:
            new_ordinal = 1
            parent = None
        else:
            new_ordinal = active_node.ordinal_number + 1
            if form.cleaned_data["make_child"]:
                parent = active_node
            else:
                parent = active_node.parentnode

        if form.cleaned_data["content"] == "0":
            with reversion.create_revision():
                page = Lecture(origin=course)
                setattr(
                    page,
                    f"name_{settings.MODELTRANSLATION_DEFAULT_LANGUAGE}",
                    form.cleaned_data["new_page_name"]
                )
                if form.cleaned_data["multi_language"]:
                    setattr(
                        page,
                        f"content_{settings.MODELTRANSLATION_DEFAULT_LANGUAGE}",
                        f"= {form.cleaned_data['new_page_name']} ="
                    )
                    for lang_code, __ in settings.LANGUAGES:
                        if lang_code != settings.MODELTRANSLATION_DEFAULT_LANGUAGE:
                            setattr(page, f"content_{lang_code}", "TBD")

                page.save()
                reversion.set_user(request.user)
        else:
            try:
                page = Lecture.objects.get(id=form.cleaned_data["content"])
            except Lecture.DoesNotExist:
                return HttpResponseNotFound()

        new_node = form.save(commit=False)
        new_node.instance = instance
        new_node.ordinal_number = new_ordinal
        new_node.content = page
        new_node.parentnode = parent

        after = ContentGraph.objects.filter(
            instance=instance,
            ordinal_number__gte=new_ordinal,
            parentnode=new_node.parentnode,
        ).order_by("ordinal_number")
        for node in after:
            node.ordinal_number += 1
            node.save()

        new_node.save()
        new_node.content.update_embedded_links(instance)
        instance.clear_content_tree_cache()
        return JsonResponse({"status": "ok"}, status=201)

    form = NewContentNodeForm(available_content=available_content, course_instance=instance)
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "courses:create_content_node", kwargs={"course": course, "instance": instance}
        ),
        "html_id": "toc-new-node-form",
        "html_class": "toc-form staff-only",
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def remove_content_node(request, course, instance, node_id):
    if request.method == "POST":
        try:
            node = ContentGraph.objects.get(id=node_id, instance=instance)
            EmbeddedLink.objects.filter(parent=node.content, instance=instance).delete()
            node.delete()
            instance.clear_content_tree_cache()
        except ContentGraph.DoesNotExist:
            return HttpResponseNotFound(_("This content node doesn't exist"))
        return HttpResponse(status=204)
    return HttpResponseNotAllowed(["POST"])


@ensure_staff
def node_settings(request, course, instance, node_id):
    content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
    available_content = content_access.defer("content").all()
    try:
        node = ContentGraph.objects.get(id=node_id, instance=instance)
    except ContentGraph.DoesNotExist:
        return HttpResponseNotFound(_("This content node doesn't exist"))

    if request.method == "POST":
        form = NodeSettingsForm(request.POST, available_content=available_content, instance=node)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        node = form.save(commit=False)
        try:
            content = ContentPage.objects.get(id=form.cleaned_data["content"])
        except ContentPage.DoesNotExist:
            return HttpResponseNotFound()
        node.content = content
        node.save()
        instance.clear_content_tree_cache()
        return JsonResponse({"status": "ok"})

    form = NodeSettingsForm(
        instance=node, available_content=available_content, initial={"content": node.content.id}
    )
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": reverse(
            "courses:node_settings",
            kwargs={"course": course, "instance": instance, "node_id": node_id},
        ),
        "html_id": "toc-node-settings-form",
        "html_class": "toc-form staff-only",
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(t.render(c, request))


@ensure_staff
def move_content_node(request, course, instance, target_id, placement):
    if not request.method == "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        active_node = ContentGraph.objects.get(instance=instance, id=request.POST["active_node"])
        target_node = ContentGraph.objects.get(instance=instance, id=target_id)
    except ContentGraph.DoesNotExist:
        return HttpResponseNotFound()

    if active_node == target_node:
        return HttpResponseBadRequest(_("Cannot move a node to itself"))

    parent = target_node.parentnode
    while parent is not None:
        if parent == active_node:
            return HttpResponseBadRequest(_("Cannot move a node inside its own branch"))
        parent = parent.parentnode

    if placement == "child":
        current_children = ContentGraph.objects.filter(
            instance=instance,
            parentnode=target_node,
        ).order_by("ordinal_number")
        for i, child in enumerate(current_children):
            child.ordinal_number = target_node.ordinal_number + (2 + i)
            child.save()

        active_node.parentnode = target_node
        active_node.ordinal_number = target_node.ordinal_number + 1
        active_node.save()
        instance.clear_content_tree_cache()
        return JsonResponse({"status": "ok"})

    if placement == "after":
        new_ordinal = target_node.ordinal_number + 1
    elif placement == "before":
        new_ordinal = target_node.ordinal_number
    else:
        return HttpResponseBadRequest()

    after = ContentGraph.objects.filter(
        instance=instance,
        ordinal_number__gte=new_ordinal,
        parentnode=target_node.parentnode,
    ).order_by("ordinal_number")

    for node in after:
        node.ordinal_number += 1
        node.save()

    active_node.ordinal_number = new_ordinal
    active_node.parentnode = target_node.parentnode
    active_node.save()

    instance.clear_content_tree_cache()

    return JsonResponse({"status": "ok"})


# ^
# |
# CONTENT NODE MANAGEMENT VIEWS
# PAGE CONTENT MANAGEMENT VIEWS
# |
# v




@ensure_responsible
def regen_page_cache(request, course, instance, content):
    if request.method == "POST":
        form = CacheRegenForm(request.POST)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        node = ContentGraph.objects.get(instance=instance, content=content)
        if node.revision is None or form.cleaned_data["regen_archived"]:
            content.regenerate_cache(instance)
        return redirect(
            reverse(
                "courses:content",
                kwargs={"course": course, "instance": instance, "content": content},
            )
        )

    form = CacheRegenForm()
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_class": "side-panel-form",
        "disclaimer": _("Regenerate cache for {content}").format(content=content.name),
        "submit_label": _("Execute"),
        "submit_override": "toc.submit_form",
    }
    return HttpResponse(form_t.render(form_c, request))


@ensure_staff
def edit_form(request, course, instance, content, action):
    context = {
        "course": course,
        "instance": instance,
        "content": content,
        "request": request,
    }

    try:
        node = ContentGraph.objects.get(instance=instance, content=content)
    except ContentGraph.DoesNotExist:
        node = EmbeddedLink.objects.filter(instance=instance, embedded_page=content).first()

    if node.revision is not None:
        return HttpResponse(_("Cannot edit content through archived pages"))

    if request.method == "POST":
        block_type = request.POST.get("block_type")
        position = {
            "line_idx": int(request.POST.get("line_idx")),
            "line_count": int(request.POST.get("line_count")),
            "placement": request.POST.get("placement")
        }
        form = get_form(
            block_type, position, context, action, request.POST, request.FILES,
        )
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        with reversion.create_revision():
            save_form(form)
            place_into_content(content, form)
            reversion.set_user(request.user)
        regenerate_nearest_cache(content)
        instance.clear_content_tree_cache()
        squash_revisions(content, 1)
        return JsonResponse({"status": "ok"})

    block_type = request.GET.get("block")
    position = {
        "line_idx": int(request.GET.get("line")),
        "line_count": int(request.GET.get("size")),
        "placement": request.GET.get("placement", "replace")
    }
    form =get_form(
        block_type, position, context, action
    )
    form_t = loader.get_template("courses/base-edit-form.html")
    form_id = f"line-edit-form"
    form_c = {
        "html_id": form_id,
        "form_object": form,
        "submit_url": request.path,
        "html_class": "side-panel-form edit-form-widget",
        "submit_label": _("Save"),
        "submit_override": "editing.submit_form"
    }
    return HttpResponse(form_t.render(form_c, request))


@ensure_staff
def add_form(request, course, instance, content):
    if request.method == "POST":
        line_idx = int(request.POST.get("line_idx"))
        line_count = int(request.POST.get("line_count"))
        form = BlockTypeSelectForm(request.POST, line_idx=line_idx)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        query = (
            f"?line={form.cleaned_data['line_idx']}"
            f"&block={form.cleaned_data['block_type']}"
            f"&placement={form.cleaned_data['placement']}"
            f"&size={form.cleaned_data['line_count']}"
        )
        disclaimer = ""
        if form.cleaned_data["mode"] == "create":
            action = "add"
        elif form.cleaned_data["block_type"] in markupparser.MarkupParser.include_forms:
            action = "include"
        else:
            action = "add"

        form_url = reverse(
            "courses:content_edit_form",
            kwargs={
                "course": course,
                "instance": instance,
                "content": content,
                "action": action,
            },
        )
        return JsonResponse({"status": "ok", "form_url": form_url + query})

    line_idx = int(request.GET.get("line"))
    line_count = int(request.GET.get("size"))
    form = BlockTypeSelectForm(line_idx=line_idx, line_count=line_count)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_id = f"line-add-form"
    form_c = {
        "html_id": form_id,
        "form_object": form,
        "submit_url": request.path,
        "html_class": "side-panel-form",
        "submit_label": _("Get form"),
        "submit_override": "editing.get_form_url"
    }
    return HttpResponse(form_t.render(form_c, request))


# ^
# |
# PAGE CONTENT MANAGEMENT VIEWS
# GROUP MANAGEMENT VIEWS
# |
# v


@ensure_staff
def group_management(request, course, instance):
    if request.user == course.main_responsible or request.user.is_superuser:
        groups = StudentGroup.objects.filter(instance=instance).order_by("name")
        responsible = True
        staff_members = course.staff_group.user_set.get_queryset().order_by("last_name")
    else:
        groups = StudentGroup.objects.filter(instance=instance, supervisor=request.user).order_by(
            "name"
        )
        responsible = False
        staff_members = User.objects.none()

    t = loader.get_template("courses/group-management.html")
    c = {
        "groups": groups,
        "course": course,
        "instance": instance,
        "is_responsible": responsible,
        "staff": staff_members,
        "course_staff": True,
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def create_group(request, course, instance):
    staff_members = course.staff_group.user_set.get_queryset().order_by("last_name")
    if request.method == "POST":
        form = GroupForm(request.POST, staff=staff_members)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        group = form.save(commit=False)
        if int(form.cleaned_data["supervisor"]):
            group.supervisor = User.objects.get(id=form.cleaned_data["supervisor"])
        group.instance = instance
        group.save()
        return JsonResponse({"status": "ok"})

    form = GroupForm(staff=staff_members)
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": request.path,
        "html_class": "group-staff-form",
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def remove_group(request, course, instance, group):
    if group.instance == instance:
        group.delete()
        return JsonResponse({"status": "ok"})
    return HttpResponseForbidden()


@ensure_responsible_or_supervisor
def add_member(request, course, instance, group):
    enrolled_students = instance.enrolled_users.get_queryset()
    if request.method == "POST":
        form = GroupMemberForm(request.POST, students=enrolled_students)
        if not form.is_valid(instance):
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        user = enrolled_students.get(id=form.cleaned_data["student"])


        group.members.add(user)
        return JsonResponse(
            {
                "redirect": reverse(
                    "courses:group_management", kwargs={"course": course, "instance": instance}
                )
            }
        )

    form = GroupMemberForm(students=enrolled_students)
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "form_object": form,
        "submit_url": request.path,
        "html_class": "group-staff-form",
    }
    return HttpResponse(t.render(c, request))


@ensure_responsible
def set_supervisor(request, course, instance, group):
    if group.instance != instance:
        return HttpResponseForbidden()

    staff_members = course.staff_group.user_set.get_queryset().order_by("last_name")
    try:
        supervisor = staff_members.get(id=request.POST["extra[supervisor]"])
    except User.DoesNotExist:
        return HttpResponseForbidden()

    group.supervisor = supervisor
    group.save()
    return JsonResponse({"status": "ok"})


@ensure_responsible_or_supervisor
def remove_member(request, course, instance, group, member):
    group.members.remove(member)
    return JsonResponse({"status": "ok"})


@ensure_responsible_or_supervisor
def rename_group(request, course, instance, group):
    name = request.POST.get("extra[name]")
    if name:
        group.name = name
        group.save()
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "error", "reason": "empty"})


# ^
# |
# GROUP MANAGEMENT VIEWS
# OTHER
# |
# v


def content_preview(request, field_name):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden(_("Only staff members can access this view"))

    try:
        content = request.POST["content"]
    except KeyError:
        return HttpResponseBadRequest(_("No content to show"))

    question = request.POST.get("question", "")
    lang_code = field_name[-2:]
    embedded_preview = request.POST.get("embedded", False)

    with translation.override(lang_code):
        parser = markupparser.MarkupParser()
        markup_gen = parser.parse(content)
        segment = ""
        pages = []
        blocks = []

        for chunk in markup_gen:
            blocks.append(chunk)

            #if isinstance(chunk, str):
                #segment += chunk
            #elif isinstance(chunk, markupparser.PageBreak):
                #blocks.append(("plain", segment))
                #segment = ""
                #pages.append(blocks)
                #blocks = []
            #else:
                #blocks.append(("plain", segment))
                #blocks.append(chunk)
                #segment = ""

        #if segment:
            #blocks.append(("plain", segment))

        pages.append(blocks)
        full = [block for page in pages for block in page]

        if question:
            rendered_question = blockparser.parseblock(escape(question, quote=False), {})
        else:
            rendered_question = ""

        t = loader.get_template("courses/content-preview.html")
        c = {
            "content_blocks": full,
        }
        if embedded_preview:
            template = request.POST["form_template"]
            form = loader.get_template(template)
            choices = []
            for i, choice in enumerate(request.POST.getlist("choices[]")):
                if choice:
                    choices.append({"id": i, "answer": choice})
            c["embedded_preview"] = True
            c["embed_data"] = {
                "content": full,
                "question": rendered_question,
                "form": form.render({"choices": choices}, request),
            }

        rendered = t.render(c, request)

    return HttpResponse(rendered)
