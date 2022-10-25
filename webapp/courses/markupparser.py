"""
Parser for wiki markup block content, i.e. paragraphs, bullet lists, tables, etc.
Idea from http://wiki.sheep.art.pl/Wiki%20Markup%20Parser%20in%20Python
"""

# TODO: Rework the registering of the different markups. Allow plugins to register
# additional markups from their own files.

# TODO: When the markup has been fully parsed, provide an object with an interface
# which allows the user to get iterators/lists of embedded objects (names and options)
# in the parsed document. This will make it easier to get and update the graph of
# embedded pages.

# TODO: Rework the parser into a plugin-extensible general Python library.

# TODO: Provide example objects with lovelace-internal-<> like identifiers.

import re
import itertools
import operator
import copy
#from django.utils.html import escape # Escapes ' characters -> prevents inline parsing
# Possible solution: Import above as strict_escape and below as body_escape
from html import escape # Use this instead? Security? HTML injection?

from django.template import loader
from django.urls import reverse
from django.utils.safestring import mark_safe

from django.utils.text import slugify as slugify

import pygments
from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
from pygments.formatters import HtmlFormatter

from reversion import revisions as reversion
from reversion.models import Version

import courses.blockparser as blockparser
import courses.models as cm
import feedback.models

from utils.archive import get_single_archived
from utils.content import get_embedded_media_file, get_embedded_media_image

# TODO: Support indented blocks (e.g. <pre>) within indents, uls & ols
# TODO: Support admonitions/warnings/good to know boxes/etc.
# TODO: Support tags that, when hovered, highlight lines in source code files
# TODO: Support tags that get highlighted upon receiving hints
# TODO: Support tags for monospace ASCII art with horizontal and vertical rulers
#       and a grid background (linear-gradients)
# TODO: Support full-width option for embedded content (e.g. images) so that they can
#       take up the whole white column space.
# TODO: Support tags that display files as hexdumps
# TODO: Generate the regexes automatically from given options etc. à la Python's argparse

class ParserUninitializedError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class InvalidParserError(Exception):
    # TODO: Add the ability to trace to the defunctional regex
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MarkupError(Exception):
    _type = ""
    _template = """<div class="markup-error">
    <div>Error in page markup: %s</div>
    <div>Description: %s</div>
</div>"""
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
    def html(self):
        return self._template % (self._type, self.value)

class PageBreak(object):
    pass
        
class UnclosedTagError(MarkupError):
    _type = "unclosed tag"

class EmbeddedObjectNotAllowedError(MarkupError):
    _type = "embedded object not allowed"
    
class EmbeddedObjectNotFoundError(MarkupError):
    _type = "embedded object not found"

class MarkupParser:
    """
    Static parser class for generating HTML from the used markup block types.

    Each markup component (given to this parser class as a markup class)
    provides its own markup as a regexp and block & settings functions. The
    markups are combined to form the markup language.
    """

    # TODO: Handle the inline markups and HTML escapes on the same pass

    # TODO: Rework the parser to use a stack based state

    _markups = {}
    _block_re = None
    _inline_re = None
    _ready = False
    
    @classmethod
    def add(cls, *markups):
        """
        Add the Markup classes given as arguments into the parser's internal
        dictionary and set the ready flag False to indicate that re-compilation
        is required.
        """
        cls._ready = False
        cls._markups.update((markup.shortname, markup) for markup in markups)

    @classmethod
    def compile(cls):
        """
        Iterate the parser's internal markup dictionary to create and compile
        the parsing regex based on individual regexes of the different Markup
        classes.
        """
        try:
            cls._block_re = re.compile(
                r"|".join(
                    r"(?P<%s>%s)" % (shortname, markup.regexp)
                    for shortname, markup in sorted(cls._markups.items())
                    if markup.regexp and not markup.inline
                )
            )
        except re.error as e:
            raise InvalidParserError("invalid regex syntax in a markup: %s" % e)

        try:
            cls._inline_re = re.compile(
                r"|".join(
                    r"(?P<%s>%s)" % (shortname, markup.regexp)
                    for shortname, markup in sorted(cls._markups.items())
                    if markup.regexp and markup.inline
                )
            )
        except re.error as e:
            raise InvalidParserError("invalid regex syntax in a markup: %s" % e)
        
        cls._ready = True

    @classmethod
    def get_markups(cls):
        return copy.deepcopy(cls._markups)

    @classmethod
    def inline_parse(cls, block):
        #yield from
        return block

    @classmethod
    def _get_line_kind(cls, line):
        """
        Key function for itertools.groupby(...)

        When a line matches the compiled regexp, select the name of the matched
        group (the shortname attribute of the specifically matching Markup) as
        the key. Otherwise, default the key to 'paragraph'.

        The match object is returned for use in the settings function of the
        markup.

        TODO: The state selection could be implemented here; just have a class-
        wide object point to the current regex-state instead of _block_re.
        """
        matchobj = cls._block_re.match(line)
        return getattr(matchobj, "lastgroup", "paragraph"), matchobj

    @classmethod
    def parse(cls, text, request=None, context=None, embedded_pages=None):
        """
        A generator that gets the text written in the markup language, splits
        it at newlines and yields the parsed text until the whole text has
        been parsed.
        """
        if not cls._ready:
            raise ParserUninitializedError("compile() not called")

        if context is None: context = {}
        if embedded_pages is None: embedded_pages = []

        # TODO: Generator version of splitter to avoid memory & CPU overhead of
        # first creating a complete list and afterwards iterating through it.
        # I.e. reduce from O(2n) to O(n)
        # Note! pypi regex has regex.splititer
        lines = iter(re.split(r"\r\n|\r|\n", text))

        # Note: stateless single-pass parsing of HTML-like languages is
        # impossible because of the closing tags.
        # TODO: Initialize states from markups
        # TODO: State stack for indents, inline markups, pre, etc.
        state = {"lines": lines, "request": request, "context": context,
                 "list": [], "embedded_pages": embedded_pages, "table": False}

        for (block_type, matchobj), block in itertools.groupby(lines, cls._get_line_kind):
            block_markup = cls._markups[block_type]
            block_func = block_markup.block
            
            # TODO: Modular cleanup of indent, ul, ol, table etc.
            if block_type != "list":
                for undent_lvl in reversed(state["list"]):
                    yield '</%s>' % undent_lvl
                state["list"] = []
            if block_type != "table" and state["table"]:
                yield '</table>\n'
                state["table"] = False

            block = cls.inline_parse(block) if block_markup.allow_inline\
                    else block
            
            try:
                settings = cls._markups[block_type].settings(matchobj, state)
                yield from block_func(block, settings, state)
            except MarkupError as e:
                yield e.html()

        # Clean up the remaining open tags (pop everything from stack)
        for undent_lvl in reversed(state["list"]):
            yield '</%s>' % undent_lvl
        if state["table"]:
            yield '</table>\n'
            
markups = []
link_markups = []

class LinkParser(MarkupParser):
    """
    Lite version of MarkupParser. This is used for parsing embedded links to
    content and media objects for the purpose of creating context objects:
     - EmbeddedLink for embedded content
     - CourseMediaLink for embedded media files
    """
    
    _markups = {}
    
    @classmethod
    def parse(cls, text, instance=None):
        if not cls._ready:
            raise ParserUninitializedError("compile() not called")
        
        page_links = []
        media_links = []
        
        lines = iter(re.split(r"\r\n|\n\r", text))
        
        for (block_type, matchobj), block in itertools.groupby(lines, cls._get_line_kind):
            try:
                block_markup = cls._markups[block_type]
            except KeyError:
                pass
            else:
                link_func = block_markup.build_links
                link_func(block, matchobj, instance, page_links, media_links)
            
        return page_links, media_links
            
        
    
    
    



# inline = this markup is inline
# allow_inline = if use of inline markup, such as <b> is allowed
class Markup:
    """
    Base class for the markups.

    The below metadata is used for documentation purposes. E.g. the example is
    displayed both as rendered and without rendering.
    """
    name = ""
    shortname = ""
    description = ""
    regexp = r""
    markup_class = ""
    example = ""
    states = {}
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        pass

    @classmethod
    def settings(cls, matchobj, state):
        pass

class BoldMarkup(Markup):
    name = "Bold"
    shortname = "bold"
    description = "Bold text"
    regexp = r"[*]{2}.+[*]{2}"
    markup_class = "inline"
    example = ""
    states = {}
    inline = True
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        pass

    @classmethod
    def settings(cls, matchobj, state):
        pass

markups.append(BoldMarkup)

class CalendarMarkup(Markup):
    name = "Calendar"
    shortname = "calendar"
    description = "A calendar for time reservations."
    regexp = r"^\<\!calendar\=(?P<calendar_name>[^\s>]+)\>\s*$"
    markup_class = "embedded item"
    example = "<!calendar=course-project-demo-calendar>"
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        # TODO: replace by form validation for calendar links
        try:
            calendar = cm.Calendar.objects.get(name=settings["calendar_name"])
        except cm.Calendar.DoesNotExist:
            yield '<div>Calendar {} not found.</div>'.format(
                settings["calendar_name"]
            )
        else:
            yield ("calendar", {"calendar": settings["calendar_name"]})
    
        # all dynamic
        # v
    
        # try:
            # calendar = cm.Calendar.objects.get(name=settings["calendar_name"])
        # except cm.Calendar.DoesNotExist as e:
            # # TODO: Modular errors
            # yield '<div>Calendar {} not found.</div>'.format(
                # settings["calendar_name"]
                # )
            # return

        # calendar_dates = cm.CalendarDate.objects.filter(calendar=calendar)

        # calendar_reservations = [
            # (
                # cal_date, 
                # [cm.CalendarReservation.objects.filter(calendar_date=cal_date), False]
            # )
            # for cal_date in calendar_dates
        # ]

        # user = state["request"].user
        # user_has_slot = False
        # reserved_event_ids = []

        # if user.is_authenticated:
            # for cal_date, cal_reservations in calendar_reservations:
                # try:
                    # found = cal_reservations[0].get(user=state["request"].user)
                # except cm.CalendarReservation.DoesNotExist as e:
                    # continue
                # cal_reservations[1] = True
                # user_has_slot = True
                # reserved_event_ids.append(found.calendar_date.id)
        
        # if user_has_slot and not calendar.allow_multiple:
            # for cal_date, cal_reservations in calendar_reservations:
                # cal_reservations[1] = True
        
        # c = {
            # "cal_id": calendar.id,
            # "cal_reservations": calendar_reservations,
            # "reserved_event_ids": reserved_event_ids,
        # }
        
        # t = loader.get_template("courses/calendar.html")
        # rendered_content = t.render(c, state["request"])
        #yield rendered_content
        
        
    @classmethod
    def settings(cls, matchobj, state):
        settings = {"calendar_name" : matchobj.group("calendar_name")}
        return settings

markups.append(CalendarMarkup)

class CodeMarkup(Markup):
    # TODO: A way to change the language mid-way (e.g. a shell session with Python code in it)
    name = "Code"
    shortname = "code"
    description = "Monospaced field for code and other preformatted text. Supported syntax highlighting identifiers (look for short names): http://pygments.org/docs/lexers/"
    regexp = r"^[{]{3}(highlight=(?P<highlight>[^\s]*))?\s*$" # TODO: Better settings
    markup_class = ""
    example = "{{{highlight=python3\n"\
              "name = input(\"What is your name? \")\n"\
              "\n"\
              "print(\"Hello, {name}! Oh, and hello, world!\".format(name=name))\n"\
              "}}}"
    states = {}
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        # TODO: Code syntax highlighting
        highlight = settings["highlight"]
        yield '<pre class="normal">' # TODO: Change class!
        text = ""
        if highlight:
            try:
                lexer = get_lexer_by_name(highlight)
            except pygments.util.ClassNotFound as e:
                # TODO: Raise an error that handles this instead
                yield '<div class="warning">%s</div>' % str(e).capitalize()
                highlight = False
            else:
                yield '<code class="highlight %s-lang-highlight">' % highlight

        try:
            line = next(state["lines"])
            while not line.startswith("}}}"):
                text += line + "\n"
                line = next(state["lines"])
        except StopIteration:
            # TODO: Raise an error (and close the pre and code tags)
            yield 'Warning: unclosed code block!\n'
        if highlight:
            highlighted = pygments.highlight(text[:-1], lexer, HtmlFormatter(nowrap=True))
            yield '%s</code>' % highlighted
        else:
            yield text
        yield '</pre>\n'

    @classmethod
    def settings(cls, matchobj, state):
        settings = {}
        # TODO: define available settings in class
        # TODO: compile the final regexp from the settings
        # TODO: highlight single lines with a background colour & a symbol
        for setting in ("highlight", "line_numbers"):
            try:
                settings[setting] = matchobj.group(setting)
            except IndexError as e:
                pass
        return settings

markups.append(CodeMarkup)

class EmbeddedFileMarkup(Markup):
    name = "Embedded file"
    shortname = "file"
    description = "An embedded file, syntax highlighted and line numbered."
    regexp = r"^\<\!file\=(?P<file_slug>[^\|>]+)(\|link_only\=(?P<link_only>[^>|]+))?\>\s*$"
    markup_class = "embedded item"
    example = "<!file=my-file-name>"
    states = {}
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        instance = state["context"].get("instance")
        
        try:
            file_object = get_embedded_media_file(
                settings["file_slug"],
                instance,
                state["context"].get("content")
            )
        except cm.File.DoesNotExist as e:
            # TODO: Modular errors
            yield '<div>File %s not found.</div>' % settings["file_slug"]
            return

        file_path = file_object.fileinfo.path
        link_only = settings.get("link_only", "") == "True"

        if link_only:
            highlighted = ""
        else:           
            try:
                file_contents = open(file_path, mode='r', encoding='utf-8').read()
            except ValueError as e:
                # TODO: Modular errors
                yield "<div>Unable to decode file %s with utf-8.</div>" % settings["file_slug"]
                return

            try:
                lexer = guess_lexer_for_filename(file_path, file_contents)
            except pygments.util.ClassNotFound:
                # TODO: Modular errors
                yield '<div>Unable to find lexer for file %s.</div>' % settings['file_slug']
                return

            highlighted = pygments.highlight(
                file_contents, lexer, HtmlFormatter(nowrap=True)
            )
        
        if file_object.download_as:
            dl_name = file_object.download_as
        else:
            dl_name = file_object.name

        t = loader.get_template("courses/embedded-codefile.html")
        c = {
            "name": dl_name,
            "file": file_object,
            "instance": instance,
            "contents": mark_safe(highlighted),
            "content_lines": highlighted.split("\n"),
            "show_content": not link_only,
        }

        yield t.render(c)

    @classmethod
    def settings(cls, matchobj, state):
        settings = {"file_slug" : escape(matchobj.group("file_slug"))}
        try:
            settings["link_only"] = escape(matchobj.group("link_only"))
        except AttributeError:
            pass
        
        return settings

    @classmethod
    def build_links(cls, block, matchobj, instance, page_links, media_links):
        slug = matchobj.group("file_slug")
        media_links.append(slug)

markups.append(EmbeddedFileMarkup)
link_markups.append(EmbeddedFileMarkup)

class EmbeddedPageMarkup(Markup):
    name = "Embedded page"
    shortname = "embedded_page"
    description = "A lecture or exercise, embedded into the page in question."
    regexp = r"^\<\!page\=(?P<page_slug>[^|>]+)"\
             r"(\|rev\=(?P<revision>\d+))?" r"\>\s*$"
    markup_class = "embedded item"
    example = "<!page=slug-of-some-exercise>"
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        if "tooltip" in state["context"] and state["context"]["tooltip"]:
            raise EmbeddedObjectNotAllowedError(
                "embedded pages are not allowed in tooltips"
            )
        
#        yield '<div class="embedded-page">\n'
#        yield settings["rendered_content"]
#        yield '</div>\n'

        yield ("embedded", settings)

    @classmethod
    def settings(cls, matchobj, state):
        settings = {
            "slug": matchobj.group("page_slug")
        }
        revision = None
        instance = state["context"].get("instance")
        try:
            revision = int(matchobj.group("revision"))
        except AttributeError:
            pass
        except TypeError:
            pass #raise something about invalid revision? dunno

        try:
            try:
                link = cm.EmbeddedLink.objects.get(
                    embedded_page__slug=settings["slug"],
                    instance=instance,
                    parent=state["context"]["content"]
                )
            except (KeyError, cm.EmbeddedLink.DoesNotExist) as e:
                # link does not exist yet, get by page slug instead
                page = cm.ContentPage.objects.get(slug=settings["slug"])
            else:
                page = link.embedded_page
                revision = link.revision
            #revision = link.revision
            #page = cm.ContentPage.objects\
                                             #.get(slug=settings["page_slug"])
        except cm.ContentPage.DoesNotExist as e:
            raise EmbeddedObjectNotFoundError("embedded page '%s' couldn't be found" % settings["slug"])
        else:
            if revision is not None:
                try:
                    page = get_single_archived(page, revision)
                except Version.DoesNotExist as e:
                    raise EmbeddedObjectNotFoundError(
                        "revision '%d' of embedded page '%s' couldn't be found"
                        % (revision, settings["slug"])
                    )
            
            state["embedded_pages"].append((settings["slug"], revision))

            # TODO: Prevent recursion depth > 2
            #embedded_content = page.rendered_markup()
            choices = page.get_choices(page, revision=revision)
            c = {
                "content": page,
                "course": state["context"].get("course"),
                "instance": state["context"].get("instance"),
                "choices": choices,
                "revision": revision
            }            
            embedded_content = page.get_rendered_content(page, c)
            question = page.get_question(page, c)
            t = loader.get_template(page.template)
            rendered_form = t.render(c)
            
            settings["content"] = embedded_content
            settings["question"] = question
            settings["form"] = rendered_form
            settings["revision"] = revision
            settings["max_points"] = page.default_points
            if instance is not None:
                settings["urls"] = {
                    "stats_url": reverse("stats:single_exercise", kwargs={
                        "exercise": page
                    }),
                    "feedback_url": reverse("feedback:statistics", kwargs={
                        "instance": instance,
                        "content": page
                    }),
                    "download_url": reverse("teacher_tools:download_answers", kwargs={
                        "course": instance.course,
                        "instance": instance,
                        "content": page
                    }),
                    "summary_url": reverse("teacher_tools:answer_summary", kwargs={
                        "course": instance.course,
                        "instance": instance,
                        "content": page
                    }),
                    "edit_url": page.get_admin_change_url(),
                    "submit_url": reverse("courses:check", kwargs={
                        "course": instance.course,
                        "instance": instance,
                        "content": page,
                        "revision": revision or "head"
                    })
                }                

            # This part is dynamic
            # v
            
            # try:
                # user = state["request"].user
            # except AttributeError:
                # c["sandboxed"] = False
                # c["evaluation"] = "unanswered"
                # c["answer_count"] = 0
            # else:
                # sandboxed = state["request"].path.startswith("/sandbox/")
                # if sandboxed and user.is_authenticated and user.is_active and user.is_staff:
                    # c["sandboxed"] = True
                # elif sandboxed and (not user.is_authenticated or not user.is_active or not user.is_staff):
                    # settings["rendered_content"] = ""
                    # return settings
                # else:
                    # c["sandboxed"] = False

                # if user.is_active and page.is_answerable() and not sandboxed:
                    # c["evaluation"] = page.get_user_evaluation(page, user, instance)
                    # c["answer_count"] = page.get_user_answers(page, user, instance).count()
                # else:
                    # c["evaluation"] = "unanswered"
                    # c["answer_count"] = 0
               
            # c.update(state["context"])
            
            # ^
            # End dynamic part
            
        return settings

    @classmethod
    def build_links(cls, block, matchobj, instance, page_links, media_links):
        slug = matchobj.group("page_slug")
        page_links.append(slug)
        

markups.append(EmbeddedPageMarkup)
link_markups.append(EmbeddedPageMarkup)

# TODO: Support embeddable JavaScript apps (maybe in iframe?)
# - http://www.html5rocks.com/en/tutorials/security/sandboxed-iframes/
# - https://developer.mozilla.org/en-US/docs/Web/API/window.postMessage
# TODO: support archived versions?
class EmbeddedScriptMarkup(Markup):
    name = "Embedded script"
    shortname = "script"
    description = "An embedded script, contained inside an iframe."
    regexp = r"^\<\!script\=(?P<script_slug>[^\|>]+)(\|width\=(?P<script_width>[^>|]+))?"\
             r"(\|height\=(?P<script_height>[^>|]+))?(\|border\=(?P<border>[^>|]+))?"\
             r"(\|include\=(?P<include>[^>|]+))?" r"\>\s*$"
    markup_class = "embedded item"
    example = "<!script=dijkstra-clickable-demo>"
    states = {}
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        if "tooltip" in state["context"] and state["context"]["tooltip"]:
            raise EmbeddedObjectNotAllowedError("embedded scripts are not allowed in tooltips")
        

        instance = state["context"].get("instance")
        content = state["context"].get("content")
        
        
        try:
            script = get_embedded_media_file(settings["script_slug"], instance, content)
        except cm.File.DoesNotExist as e:
            # TODO: Modular errors
            yield '<div>File %s not found.</div>' % settings["script_slug"]
            return

        includes = []
        image_urls = []
        unparsed_includes = settings.get("include") or []
        for unparsed_include in unparsed_includes:
            try:
                where, t_and_n = unparsed_include.split(":")
                incl_type, incl_name = t_and_n.split("=")
            except ValueError:
                # TODO: Modular errors
                yield '<div>Erroneous form {} in a script markup.</div>'.format(unparsed_include)
                return

            try:
                if incl_type == "image":                
                    incl_obj = get_embedded_media_image(incl_name, instance, content)
                else:
                    incl_obj = get_embedded_media_file(incl_name, instance, content)
            except (cm.File.DoesNotExist, cm.Image.DoesNotExist) as e:
                # TODO: Modular errors
                yield '<div>{} {} not found.</div>'.format(incl_type.capitalize(), incl_name)
                return

            incl_addr = escape(incl_obj.fileinfo.url)

            if incl_type == "script":
                includes.append(
                    #(where, "<script src='{addr}'><\" + \"/script>".format(addr=escape(incl_addr)))
                    ("script", incl_name, "type", "text/javascript", "src", incl_addr, where)
                )
            elif incl_type == "style":
                includes.append(
                    #(where, "<link rel='stylesheet' href='{addr}'>".format(addr=escape(incl_addr)))
                    ("link", incl_name, "rel", "stylesheet", "href", incl_addr, where)
                )
            elif incl_type == "image":
                image_urls.append(
                    (incl_name, incl_addr, where)
                )

        # TODO: In an edge case, using the same parameters will cause an id clash
        # TODO: Also the md5 will rarely cause an id clash
        import hashlib
        hash_includes = hashlib.md5("".join(unparsed_includes).encode("utf-8")).hexdigest()
        iframe_id = escape(script.name + "-" + hash_includes)
        
        # TODO: Change the include file names into slugs to prevent spaces!
        tag = '<iframe id="{id}" src="{addr}" sandbox="allow-same-origin allow-scripts"'.format(
            id=iframe_id, addr=escape(script.fileinfo.url)
        )
        if "width" in settings:
            tag += ' width="%s"' % settings["width"]
        if "height" in settings:
            tag += ' height="%s"' % settings["height"]
        if "border" in settings:
            tag += ' frameborder="%s"' % settings["border"]
        tag += "></iframe>\n"

        # TODO: Could this cause a race condition?
        if includes or image_urls:
            inject_includes_template = """<script>
(function() {{
  var script_iframe = $("#{id}");
  
  var script_iframe_inject_function = function() {{
    var cw = script_iframe[0].contentWindow.document;
{injects}
  }};
  script_iframe.on("load", script_iframe_inject_function);
}})();
</script>
"""

            single_inject_template = \
"""    var new_{num} = cw.createElement("{type}");
    new_{num}.{type_type} = "{type_value}";
    new_{num}.{src_type} = "{addr}";
    new_{num}.id = "id-{name}";
    cw.getElementsByTagName("{where}")[0].appendChild(new_{num});
"""

            inject_images_template = \
"""    var new_img_addresses = cw.createElement("script");
    new_img_addresses.innerHTML = '{img_addrs}';
    new_img_addresses.id = "id-img_addrs";
    cw.getElementsByTagName("{where}")[0].appendChild(new_img_addresses);
"""
            single_image_inject_template = "var src_{name} = \"{addr}\";"  # TODO: Bug with names that have a '-'
            array_image_injects_template = "var img_srcs = [{var_names}];" # TODO: Bug with names that have a '-'
            
            injects = "\n".join(
                single_inject_template.format(
                    type=t,
                    name=slugify(n, allow_unicode=True),
                    num=i,
                    type_type=tt,
                    type_value=tv,
                    src_type=st,
                    addr=a,
                    where=w
                )
                for i, (t, n, tt, tv, st, a, w) in enumerate(includes)
            )
            if image_urls:
                image_includes = inject_images_template.format(
                    where=image_urls[0][2], # Just take the first
                    img_addrs="\\\n".join(
                        single_image_inject_template.format(name=n, addr=a)
                        for n, a, _ in image_urls
                    ) + array_image_injects_template.format(
                        var_names=", ".join(
                            "src_" + n
                            for n, _, _ in image_urls
                        )
                    )
                )
                injects += "\n" + image_includes
            
            rendered_includes = inject_includes_template.format(
                id=iframe_id,
                injects=injects
            )
            tag += rendered_includes

        yield tag

    @classmethod
    def settings(cls, matchobj, state):
        settings = {"script_slug" : escape(matchobj.group("script_slug"))}
        try:
            settings["width"] = escape(matchobj.group("script_width"))
        except AttributeError:
            pass
        try:
            settings["height"] = escape(matchobj.group("script_height"))
        except AttributeError:
            pass
        try:
            settings["border"] = escape(matchobj.group("border"))
        except AttributeError:
            pass
        try:
            settings["include"] = escape(matchobj.group("include")).split(",")
        except AttributeError:
            pass
        return settings
    
    @classmethod
    def build_links(cls, block, matchobj, instance, page_links, media_links):
        slugs = [matchobj.group("script_slug")]\
                + [m.split("=")[1] for m in matchobj.group("include").split(",")]
        
        for slug in slugs:
            media_links.append(slug)

markups.append(EmbeddedScriptMarkup)
link_markups.append(EmbeddedScriptMarkup)

class EmbeddedVideoMarkup(Markup):
    name = "Embedded video"
    shortname = "video"
    description = "An embedded video, contained inside an iframe."
    regexp = r"^\<\!video\=(?P<video_slug>[^\|>]+)(\|width\=(?P<video_width>[^>|]+))?"\
             r"(\|height\=(?P<video_height>[^>|]+))?\>\s*$"
    markup_class = "embedded item"
    example = "<!video=my-video-link-name>"
    states = {}
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        if "tooltip" in state["context"] and state["context"]["tooltip"]:
            raise EmbeddedObjectNotAllowedError("embedded videos are not allowed in tooltips")
        
        try:
            videolink = cm.VideoLink.objects.get(name=settings["video_slug"])
        except cm.VideoLink.DoesNotExist as e:
            # TODO: Modular errors
            yield '<div>Video link %s not found.</div>' % settings["video_slug"]
            return

        video_url = videolink.link
        tag = '<iframe src="%s"' % video_url
        if "width" in settings:
            tag += ' width="%s"' % settings["width"]
        if "height" in settings:
            tag += ' height="%s"' % settings["height"]
        tag += "><p>Your browser does not support iframes.</p></iframe>\n"
        
        yield tag

    @classmethod
    def settings(cls, matchobj, state):
        settings = {"video_slug" : escape(matchobj.group("video_slug"))}
        try:
            settings["width"] = escape(matchobj.group("video_width"))
        except AttributeError:
            pass
        try:
            settings["height"] = escape(matchobj.group("video_height"))
        except AttributeError:
            pass
        return settings

    @classmethod
    def build_links(cls, block, matchobj, instance, page_links, media_links):
        slug = matchobj.group("video_slug")
        media_links.append(slug)


markups.append(EmbeddedVideoMarkup)
link_markups.append(EmbeddedVideoMarkup)

class EmptyMarkup(Markup):
    name = "Empty"
    shortname = "empty"
    description = "(Empty and whitespace only rows.)"
    regexp = "^\s*$"
    markup_class = ""
    example = ""
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        yield ''

    @classmethod
    def settings(cls, matchobj, state):
        pass

markups.append(EmptyMarkup)

class HeadingMarkup(Markup):
    name = "Heading"
    shortname = "heading"
    description = ""
    regexp = r"^\s*(?P<level>\={1,6})\=*\s*.+\s*(?P=level)\s*$"
    markup_class = ""
    example = "= 1st Level Heading =\n"\
              "== 2nd Level Heading ==\n"\
              "=== 3rd Level Heading ===\n"\
              "==== 4th Level Heading ====\n"\
              "===== 5th Level Heading =====\n"\
              "====== 6th Level Heading ======\n"    
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        heading = ''
        for line in block:
            heading += escape(line.strip("= \r\n\t"))
        slug = slugify(heading, allow_unicode=True)
        # TODO: Add "-heading" to id
        yield '<h%d class="content-heading">' % (settings["heading_level"])
        yield heading
        if not "tooltip" in state["context"]:
            yield '<span id="%s" class="anchor-offset"></span>' % (slug)
            yield '<a href="#%s" class="permalink" title="Permalink to %s">&para;</a>' % (slug, heading)
        yield '</h%d>\n' % settings["heading_level"]
    
    @classmethod
    def settings(cls, matchobj, state):
        settings = {"heading_level" : len(matchobj.group("level"))}
        return settings

markups.append(HeadingMarkup)

class ImageMarkup(Markup):
    name = "Image"
    shortname = "image"
    description = "An image, img tag in HTML."
    regexp = r"^\<\!image\=(?P<image_name>[^>|]+)"\
             r"(\|alt\=(?P<alt_text>[^|]+))?"\
             r"(\|caption\=(?P<caption_text>(([\[]{2}[^|]+(\|.+)?[\]]{2})|([^|]))+))?"\
             r"(\|align\=(?P<align>[^|]+))?\>\s*$"
    markup_class = "embedded item"
    example = "<!image=name-of-some-image.png|alt=alternative text|caption=caption text>"
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        instance = state["context"].get("instance")
        try:
            image_object = get_embedded_media_image(
                settings["image_name"],
                instance,
                state["context"].get("content")
            )
        except cm.Image.DoesNotExist as e:
            # TODO: Modular errors
            yield '<div>File %s not found.</div>' % settings["image_name"]
            return

        image_url = image_object.fileinfo.url
        w = image_object.fileinfo.width
        h = image_object.fileinfo.height

        MAX_IMG_WIDTH = 1000 # TODO: Depend on the level of indentation

        size_attr = ""
        if w > MAX_IMG_WIDTH:
            ratio = h / w
            new_height = MAX_IMG_WIDTH * ratio
            size_attr = ' width="%d" height="%d"' % (MAX_IMG_WIDTH, new_height)

        centered = True if settings.get("align", False) == "center" else False
        
        if centered:
            yield '<div class="centered-block-outer"><div class="centered-block-middle"><div class="centered-block-inner">'

        img_cls = "figure-img" if settings.get("caption_text", False) else "content-img"
        if "caption_text" in settings:
            yield '<figure>'
        if "alt_text" in settings:
            yield '<img class="%s" src="%s" alt="%s"%s>\n' % (img_cls, image_url, settings["alt_text"], size_attr)
        else:
            yield '<img class="%s" src="%s"%s>\n' % (img_cls, image_url, size_attr)
        if "caption_text" in settings:
            yield '<figcaption>%s</figcaption>' % (settings["caption_text"])
            yield '</figure>'

        if centered:
            yield '</div></div></div>'

    @classmethod
    def settings(cls, matchobj, state):
        settings = {"image_name" : escape(matchobj.group("image_name"))}
        try:
            settings["alt_text"] = escape(matchobj.group("alt_text"), quote=False)
        except AttributeError:
            pass
        try:
            settings["caption_text"] = blockparser.parseblock(escape(matchobj.group("caption_text"), quote=False), state["context"])
        except AttributeError:
            pass
        try:
            settings["align"] = escape(matchobj.group("align"))
        except AttributeError:
            pass
        return settings

    @classmethod
    def build_links(cls, block, matchobj, instance, page_links, media_links):
        slug = matchobj.group("image_name")
        media_links.append(slug)

markups.append(ImageMarkup)
link_markups.append(ImageMarkup)

class ListMarkup(Markup):
    name = "List"
    shortname = "list"
    description = "Unordered and ordered lists."
    regexp = r"^(?P<list_level>[*#]+)(?P<text>.+)$"
    markup_class = ""
    example = "* unordered list item 1\n** indented unordered list item 1\n"\
              "# ordered list item 1\n## indented ordered list item 1\n"
    states = {"list" : []}
    inline = False
    allow_inline = True

    @classmethod
    def block(cls, block, settings, state):
        tag = settings["tag"]

        if len(state["list"]) < settings["level"]:
            for new_lvl in range(settings["level"] - len(state["list"])):
                state["list"].append(tag)
                yield '<%s>' % tag
        elif len(state["list"]) > settings["level"]:
            for new_lvl in range(len(state["list"]) - settings["level"]):
                top_tag = state["list"].pop()
                yield '</%s>' % top_tag
        
        if len(state["list"]) == settings["level"]:
            if state["list"][-1] != tag:
                top_tag = state["list"].pop()
                yield '</%s>' % top_tag
                
                state["list"].append(tag)
                yield '<%s>' % tag
        
        for line in block:
            yield '<li>%s</li>' % blockparser.parseblock(
                escape(line.strip("*#").strip(),
                quote=False),
                state["context"]
            )

    @classmethod
    def settings(cls, matchobj, state):
        list_level = matchobj.group("list_level")
        settings = {"level" : len(list_level),
                    #"text" : matchobj.group("text").strip(),
                    "tag" : "ul" if list_level[-1] == "*" else "ol"}
        return settings

markups.append(ListMarkup)

class PageBreakMarkup(Markup):
    name = "Page break"
    shortname = "pagebreak"
    description = "Used to partition long content into several pages"
    regexp = r"~~"
    markup_class = "meta"
    example = "~~"
    inline = False
    allow_inline = False
    
    @classmethod
    def block(cls, block, settings, state):
        yield PageBreak()
        
    @classmethod
    def settings(cls, matchobj, state):
        pass

markups.append(PageBreakMarkup)

class ParagraphMarkup(Markup):
    name = "Paragraph"
    shortname = "paragraph"
    description = "A paragraph of text, equivalent of a p tag in HTML."
    regexp = r""
    markup_class = "text"
    example = "Text without any of the block level markups."
    inline = False
    allow_inline = True

    @classmethod
    def block(cls, block, settings, state):
        yield '<div class="paragraph">'
        paragraph = ""
        paragraph_lines = []
        for line in block:
            paragraph_lines.append(escape(line, quote=False))
        paragraph = "<br>\n".join(paragraph_lines)
        paragraph = blockparser.parseblock(paragraph, state["context"])
        yield paragraph
        yield '</div>\n'

    @classmethod
    def settings(cls, matchobj, state):
        pass

    @classmethod
    def build_links(cls, block, matchobj, instance, page_links, media_links):
        """
        Finds inline links to media files. Necessary to ensure that all linked
        files are provided with a context link.
        """
        
        for line in block:
            for tag in blockparser.tags["anchor"].re.findall(line):
                if tag[0].startswith("file:"):
                    media_links.append(tag[0].split("file:")[1])

markups.append(ParagraphMarkup)
link_markups.append(ParagraphMarkup)

class SeparatorMarkup(Markup):
    name = "Separator"
    shortname = "separator"
    description = "A separating horizontal line, hr tag in HTML."
    regexp = r"^\s*\-{2}\s*$"
    markup_class = "miscellaneous"
    example = "--"
    inline = False
    allow_inline = False
    
    @classmethod
    def block(cls, block, settings, state):
        yield '<hr>\n'

    @classmethod
    def settings(cls, matchobj, state):
        pass

markups.append(SeparatorMarkup)

class SvgMarkup(Markup):
    name = "SVG"
    shortname = "svg"
    description = "A block containing SVG."
    regexp = r"^[{]{3}svg\|width=(?P<svg_width>[0-9]+)\|height=(?P<svg_height>[0-9]+)\s*$"
    markup_class = ""
    example = ""
    inline = False
    allow_inline = False
    
    @classmethod
    def block(cls, block, settings, state):
        yield '<svg width="{width}" height="{height}">\n'.format(**settings)
        text = ""
        try:
            line = next(state["lines"])
            while not line.startswith("}}}"):
                yield line + "\n"
                line = next(state["lines"])
        except StopIteration:
            # TODO: Raise an error (and close the pre and code tags)
            yield 'Warning: unclosed SVG block!\n'
        yield '</svg>\n'
        
    @classmethod
    def settings(cls, matchobj, state):
        return {
            "width": matchobj.group("svg_width"),
            "height": matchobj.group("svg_height")
        }
        
markups.append(SvgMarkup)    

class TableMarkup(Markup):
    name = "Table"
    shortname = "table"
    description = "A table for representing tabular information."
    regexp = r"^[|]{2}([^|]+[|]{2})+\s*$"
    markup_class = ""
    example = "|| Heading 1 || Heading 2 ||"
    states = {}
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        if not state["table"]:
            yield '<table class="content-table">'
            state["table"] = True
        
        for line in block:
            row = line.split("||")[1:-1]
            yield '<tr>'
            yield '\n'.join("<td>%s</td>" % blockparser.parseblock(escape(cell, quote=False), state["context"]) for cell in row)
            yield '</tr>'
            
        #yield '</table>'

    @classmethod
    def settings(cls, matchobj, state):
        pass

markups.append(TableMarkup)

class TeXMarkup(Markup):
    name = "TeX"
    shortname = "tex"
    description = "TeX markup with KaTeX: https://github.com/Khan/KaTeX/wiki/Function-Support-in-KaTeX"
    regexp = r"^[<]math[>]\s*$"
    markup_class = ""
    example = "<math>\nx = \dfrac{-b \pm \sqrt{b^2 - 4ac}}{2a}\n</math>"
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        yield '<div class="tex">'
        try:
            line = next(state["lines"])
            while not line.startswith("</math>"):
                yield escape(line, quote=False) + "\n"
                line = next(state["lines"])
        except StopIteration:
            # TODO: Modular, class-based warning system
            yield 'Warning: unclosed TeX block!\n'
        yield '</div>\n'

    @classmethod
    def settings(cls, matchobj, state):
        pass

markups.append(TeXMarkup)

# TODO: Add indentation support to all compatible markups.

MarkupParser.add(*markups)
MarkupParser.compile()
LinkParser.add(*link_markups)
LinkParser.compile()
