import copy
from html import escape
import itertools
import re
from courses import blockparser

class ParserUninitializedError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class InvalidParserError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class MarkupError(Exception):
    _type = ""
    _template = (
        "<div class='markup-error'>\n"
        "    <div>Error in page markup: {}</div>\n"
        "    <div>Description: {}</div>\n"
        "</div>"
    )

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    def html(self):
        return self._template.format(self._type, self.value)


class PageBreak:
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

    _markups = {}
    edit_forms = {}
    include_forms = {}
    _block_markups = []
    _inline_markups = []

    def __init__(self):
        self._current_matchobj = None
        self._state = {}

    @classmethod
    def register_markup(cls, markup_cls):
        cls._markups.update({markup_cls.shortname: markup_cls})
        if markup_cls.regexp:
            if markup_cls.inline:
                cls._inline_markups.append(markup_cls)
            else:
                cls._block_markups.append(markup_cls)

    @classmethod
    def register_form(cls, markup, action, form):
        if action == "include":
            cls.include_forms[markup] = form
        else:
            cls.edit_forms[markup] = form

    @classmethod
    def editable_markups(cls):
        return [key for (key, item) in cls._markups.items() if item.is_editable]

    @classmethod
    def get_markups(cls):
        return copy.deepcopy(cls._markups)

    def inline_parse(self, block):
        # yield from
        return block

    def _get_line_kind(self, line):
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

        for block_markup in self._block_markups:
            if matchobj := block_markup.regexp.match(line):
                self._current_matchobj = matchobj
                block_type = block_markup.shortname
                break
        else:
            block_type = self._state["open_block"]
            return block_type

        markup = self._markups[block_type]
        if self._state["open"]:
            block_type = self._state["open_block"]
            if markup is BlockCloseMarkup:
                self._state["open_block"] = "paragraph"
                self._state["open"] = False
        elif markup.is_open:
            self._state["open_block"] = block_type
            self._state["open"] = True

        return block_type

    def parse(self, text, request=None, context=None, embedded_pages=None, editable=False):
        """
        A generator that gets the text written in the markup language, splits
        it at newlines and yields the parsed text until the whole text has
        been parsed.
        """
        self._current_matchobj = None

        if context is None:
            context = {}
        if embedded_pages is None:
            embedded_pages = []

        # TODO: Generator version of splitter to avoid memory & CPU overhead of
        # first creating a complete list and afterwards iterating through it.
        # I.e. reduce from O(2n) to O(n)
        lines = iter(text.splitlines())

        self._state = {
            "lines": lines,
            "request": request,
            "context": context,
            "list": [],
            "embedded_pages": embedded_pages,
            "table": False,
            "open_block": "paragraph",
            "open": False,
            "storage": {},
        }

        line_idx = 0
        for block_type, group in itertools.groupby(lines, self._get_line_kind):
            block_markup = self._markups[block_type]
            block_func = block_markup.block
            if self._state["storage"]:
                stored_block = self._state["storage"]["block"]
                value = self._state["storage"]["value"]
                stored_markup = self._markups[stored_block]
                for closure in stored_markup.cleanup(block_type, value, self._state):
                    yield ("cleanup", closure, line_idx, 1)

            #if block_type != "list":
                #for undent_lvl in reversed(self._state["list"]):
                    #yield ("cleanup", f"</{undent_lvl}>", line_idx, 1)
                #self._state["list"] = []
            #if block_type != "table" and self._state["table"]:
                #yield ("cleanup", "</table>\n", line_idx, 1)
                #self._state["table"] = False

            block_content = ""
            try:
                settings = self._markups[block_type].settings(self._current_matchobj, self._state)
                group = list(group)
                line_count = len(group)
                for result in block_func(group, settings, self._state):
                    if isinstance(result, str):
                        block_content += result
                    else:
                        yield (*result, line_idx, line_count)
                if block_content:
                    yield (block_type, block_content, line_idx, line_count)
            except MarkupError as e:
                yield ("error", e.html(), line_idx, 1)
                line_count = 1

            line_idx += line_count

        # Clean up the remaining open tags (pop everything from stack)
        if self._state["storage"]:
            stored_block = self._state["storage"]["block"]
            value = self._state["storage"]["value"]
            stored_markup = self._markups[stored_block]
            for closure in stored_markup.cleanup(None, value, self._state):
                yield ("cleanup", closure, line_idx, 1)


        #for undent_lvl in reversed(self._state["list"]):
            #yield ("cleanup", f"</{undent_lvl}>", line_idx, 1)
        #if self._state["table"]:
            #yield ("cleanup", "</table>\n", line_idx, 1)

        if line_idx == 0:
            yield ("empty", "", 0, 0)

    def parse_to_string(self, text, request=None, context=None, embedded_pages=None, editable=False):
        parsed_string = ""
        for block in self.parse(text, request, context, embedded_pages, editable):
            if isinstance(block[1], str):
                parsed_string += block[1]
            else:
                raise ValueError("Embedded content is not allowed when parsing to string")

        return parsed_string

    def tag(self, text, replace_in, replaces, tag):
        if not self._ready:
            raise ParserUninitializedError("compile() not called")

        self._state = {
            "open_block": "paragraph",
            "open": False
        }
        lines = iter(text.splitlines())
        lines_out = []

        replaces = [
            re.compile(
                f"(?<!{tag[0]})(?P<word>[{old[0].upper()}{old[0]}]{old[1:]})(?P<punct>[- ,.?!;:])"
            ) for old in replaces
        ]

        total_n = 0
        for block_type, group in itertools.groupby(lines, self._get_line_kind):
            if block_type in replace_in:
                for line in group:
                    for old_re in replaces:
                        line, n = old_re.subn(f"{tag[0]}\\g<word>{tag[1]}\\g<punct>", line)
                    lines_out.append(line)
                    total_n += n
            else:
                lines_out.extend(list(group))

        return lines_out, total_n


class LinkParser(MarkupParser):
    """
    Lite version of MarkupParser. This is used for parsing embedded links to
    content and media objects for the purpose of creating context objects:
     - EmbeddedLink for embedded content
     - CourseMediaLink for embedded media files
    """

    _markups = {}
    _block_markups = []
    _inline_markups = []

    def parse(self, text, instance=None):
        page_links = []
        media_links = []

        lines = iter(text.splitlines())

        self._state = {
            "open_block": "paragraph",
            "open": False
        }

        for block_type, group in itertools.groupby(lines, self._get_line_kind):
            try:
                block_markup = self._markups[block_type]
            except KeyError:
                pass
            else:
                link_func = block_markup.build_links
                link_func(group, self._current_matchobj, instance, page_links, media_links)

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
    regexp = None
    markup_class = ""
    example = ""
    states = {}
    inline = False
    allow_inline = False
    is_editable = False
    is_open = False
    has_reference = False

    @classmethod
    def block(cls, block, settings, state):
        pass

    @classmethod
    def settings(cls, matchobj, state):
        pass

    def cleanup(cls, new_block, stored_value, state):
        return []


class BlockCloseMarkup(Markup):
    name = "Close"
    shortname = "close"
    description = "Closer for open-block markups"
    regexp = re.compile(r"^[}]{3}\s*$")

    @classmethod
    def block(cls, block, settings, state):
        yield ""

    @classmethod
    def settings(cls, matchobj, state):
        pass


class EmptyMarkup(Markup):
    name = "Empty"
    shortname = "empty"
    description = "(Empty and whitespace only rows.)"
    regexp = re.compile(r"^\s*$")
    markup_class = ""
    example = ""
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        yield ""

    @classmethod
    def settings(cls, matchobj, state):
        pass


class PageBreak:
    pass


class PageBreakMarkup(Markup):
    name = "Page break"
    shortname = "pagebreak"
    description = "Used to partition long content into several pages"
    regexp = re.compile(r"~~")
    markup_class = "meta"
    example = "~~"
    inline = False
    allow_inline = False

    @classmethod
    def block(cls, block, settings, state):
        yield ("pagebreak", PageBreak())

    @classmethod
    def settings(cls, matchobj, state):
        pass



MarkupParser.register_markup(BlockCloseMarkup)
MarkupParser.register_markup(EmptyMarkup)
MarkupParser.register_markup(PageBreakMarkup)
