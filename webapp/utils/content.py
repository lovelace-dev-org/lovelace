import re

from courses.models import EmbeddedLink, CourseMediaLink, TermToInstanceLink, InstanceIncludeFileToInstanceLink
from django.utils.text import slugify as slugify
from reversion.models import Version

def first_title_from_content(content_text):
    """
    Finds the first heading from a content page and returns the title. Also
    return the slugified anchor.
    """

    titlepat = re.compile("(?P<level>={1,6}) ?(?P<title>.*) ?(?P=level)")
    try:
        title = titlepat.findall(content_text)[0]
    except IndexError:
        title = ""
        anchor = ""
    else:
        anchor = slugify(title, allow_unicode=True)

    return title, anchor

def get_course_instance_tasks(instance, deadline_before=None):

    all_embedded_links = EmbeddedLink.objects.filter(instance=instance).order_by("embedded_page__name")

    task_pages = []

    content_links = instance.contents.filter(scored=True, visible=True).order_by("ordinal_number")    
    if deadline_before is not None:
        content_links = content_links.filter(deadline__lt=deadline_before)

    for content_link in content_links:
        page_task_links = all_embedded_links.filter(parent=content_link.content)
        if page_task_links:
            task_pages.append((content_link.content, page_task_links))

    return task_pages


