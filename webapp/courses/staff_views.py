from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect,\
    HttpResponseNotFound, HttpResponseForbidden, HttpResponseNotAllowed,\
    HttpResponseServerError, HttpResponseBadRequest
from django.urls import reverse
from django.utils.translation import ugettext as _
from courses.models import *
from courses.forms import *
from utils.access import ensure_staff
from utils.management import CourseContentAdmin, clone_instance_files,\
    clone_terms, clone_content_graphs
from faq.utils import clone_faq_links


# CONTENT EDIT VIEWS
# |
# v

@ensure_staff
def freeze_instance(request, course, instance):
    if request.method == "POST":
        form = InstanceFreezeForm(
            request.POST,
        )
        if form.is_valid():
            instance.freeze(freeze_to=form.cleaned_data["freeze_to"])
            instance.save()
            return JsonResponse({"status": "ok"})
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        form = InstanceFreezeForm()
        t = loader.get_template("courses/staff-edit-form.html")
        c = {
            "form_object": form,
            "submit_url": reverse("courses:freeze_instance", kwargs={
                "course": course,
                "instance": instance
            }),
            "html_id": "instance-freeze-form",
            "html_class": "toc-form",
            "disclaimer": _("Freeze this instance to reflect its state at the given date. This operation is not intended to be reversible.")
        }
        return HttpResponse(t.render(c, request))

@ensure_staff
def clone_instance(request, course, instance):
    if request.method == "POST":
        old_pk = instance.id
        form = InstanceCloneForm(
            request.POST,
            instance=instance
        )
        if form.is_valid():
            new_instance = form.save(commit=False)
            new_instance.pk = None
            new_instance.primary = False
            for lang_code, lang_name in settings.LANGUAGES:
                field = "name_" + lang_code
                setattr(new_instance, field, form.cleaned_data[field])
            new_instance.save()
            new_instance.refresh_from_db()
            old_instance = CourseInstance.objects.get(id=old_pk)
            clone_content_graphs(old_instance, new_instance)
            clone_instance_files(new_instance)
            clone_terms(new_instance)
            clone_faq_links(new_instance)
            new_url = reverse("courses:course", kwargs={
                "course": course,
                "instance": new_instance
            })
            return JsonResponse({"status": "ok", "redirect": new_url})
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        initial_names = {}
        for lang_code, lang_name in settings.LANGUAGES:
            initial_names["name_" + lang_code] = getattr(instance, "name_" + lang_code)
        
        form = InstanceCloneForm(
            instance=instance,
            initial=initial_names
        )
        t = loader.get_template("courses/staff-edit-form.html")
        c = {
            "form_object": form,
            "submit_url": reverse("courses:clone_instance", kwargs={
                "course": course,
                "instance": instance
            }),
            "html_id": "instance-clone-form",
            "html_class": "toc-form",
            "disclaimer": _("Make a clone of this course instance.")
        }
        return HttpResponse(t.render(c, request))
        

@ensure_staff
def instance_settings(request, course, instance):
    content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
    available_content = content_access.defer("content").all()

    if request.method == "POST":
        form = InstanceSettingsForm(
            request.POST,
            instance=instance,
            available_content=available_content
        )
        if form.is_valid():
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
                    content=frontpage,
                    instance=instance,
                    scored=False,
                    ordinal_number=0
                )
                fp_node.save()
            fp_node.content.update_embedded_links(instance, fp_node.revision)
            ContentGraph.objects.filter(content=frontpage, ordinal_number__gt=0).delete()
            instance.frontpage = frontpage
            instance.save()
            return JsonResponse({"status": "ok"})
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        form = InstanceSettingsForm(
            instance=instance,
            available_content=available_content,
            initial={
                "frontpage": instance.frontpage and instance.frontpage.id
            }
        )
        t = loader.get_template("courses/staff-edit-form.html")
        c = {
            "form_object": form,
            "submit_url": reverse("courses:instance_settings", kwargs={
                "course": course,
                "instance": instance
            }),
            "html_id": "instance-settings-form",
            "html_class": "toc-form",
        }
        return HttpResponse(t.render(c, request))
    

@ensure_staff
def create_content_node(request, course, instance):
    content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
    available_content = content_access.defer("content").all()

    if request.method == "POST":
        form = NewContentNodeForm(request.POST, available_content=available_content)
        if form.is_valid():
            try:
                active_node = ContentGraph.objects.get(
                    instance=instance,
                    id=form.cleaned_data["active_node"]
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
                    page = Lecture(
                        name=form.cleaned_data["new_page_name"]
                    )
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
            return JsonResponse({"status": "ok"}, status=201)
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        form = NewContentNodeForm(available_content=available_content)
        t = loader.get_template("courses/staff-edit-form.html")
        c = {
            "form_object": form,
            "submit_url": reverse("courses:create_content_node", kwargs={
                "course": course,
                "instance": instance
            }),
            "html_id": "toc-new-node-form",
            "html_class": "toc-form",
        }
        return HttpResponse(t.render(c, request))
    

@ensure_staff
def remove_content_node(request, course, instance, node_id):
    if request.method == "POST":
        try:
            ContentGraph.objects.get(
                id=node_id,
                instance=instance
            ).delete()
        except ContentGraph.DoesNotExist:
            return HttpResponseNotFound(_("This content node doesn't exist"))
        return HttpResponse(status=204)
    else:
        return HttpResponseNotAllowed(["POST"])

@ensure_staff
def node_settings(request, course, instance, node_id):
    content_access = CourseContentAdmin.content_access_list(request, ContentPage, "LECTURE")
    available_content = content_access.defer("content").all()
    try:
        node = ContentGraph.objects.get(
            id=node_id,
            instance=instance
        )
    except ContentGraph.DoesNotExist:
        return HttpResponseNotFound(_("This content node doesn't exist"))
    
    if request.method == "POST":
        form = NodeSettingsForm(request.POST, available_content=available_content, instance=node)
        if form.is_valid():
            node = form.save(commit=False)
            try:
                content = ContentPage.objects.get(id=form.cleaned_data["content"])
            except ContentPage.DoesNotExist:
                return HttpResponseNotFound()
            node.content = content
            node.save()
            return JsonResponse({"status": "ok"})
        else:
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)
    else:
        form = NodeSettingsForm(
            instance=node,
            available_content=available_content,
            initial={
                "content": node.content.id
            }
        )
        t = loader.get_template("courses/staff-edit-form.html")
        c = {
            "form_object": form,
            "submit_url": reverse("courses:node_settings", kwargs={
                "course": course,
                "instance": instance,
                "node_id": node_id
            }),
            "html_id": "toc-node-settings-form",
            "html_class": "toc-form",
        }
        return HttpResponse(t.render(c, request))
    
    
@ensure_staff
def move_content_node(request, course, instance, target_id, placement):
    if not request.method == "POST":
        return HttpResponseNotAllowed(["POST"])
        
    try:
        active_node = ContentGraph.objects.get(
            instance=instance,
            id=request.POST["active_node"]
        )
        target_node = ContentGraph.objects.get(
            instance=instance,
            id=target_id
        )
    except ContentGraph.DoesNotExist:
        return HttpResponseNotFound()
        
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
        return JsonResponse({"status": "ok"})
    else:


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
        
        return JsonResponse({"status": "ok"})
        
    
# ^
# |
# CONTENT EDIT VIEWS
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
        markup_gen = markupparser.MarkupParser.parse(content)
        segment = ""
        pages = []
        blocks = []
        
        for chunk in markup_gen:
            if isinstance(chunk, str):
                segment += chunk
            elif isinstance(chunk, markupparser.PageBreak):
                blocks.append(("plain", segment))
                segment = ""
                pages.append(blocks)
                blocks = []
            else:
                blocks.append(("plain", segment))
                blocks.append(chunk)
                segment = ""
                
        if segment:
            blocks.append(("plain", segment))
        
        pages.append(blocks)
        full = [block for page in pages for block in page]
        
        if question:
            rendered_question = blockparser.parseblock(
                escape(question, quote=False), {}
            )
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
                    choices.append({
                        "id": i,
                        "answer": choice
                    })
            print(choices)
            c["embedded_preview"] = True
            c["embed_data"] = {
                "content": "".join(block[1] for block in full),
                "question": rendered_question,
                "form": form.render({"choices": choices}, request)
            }

        rendered = t.render(c, request)

        print(rendered)

    return HttpResponse(rendered)
