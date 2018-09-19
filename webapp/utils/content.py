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
    
    
    