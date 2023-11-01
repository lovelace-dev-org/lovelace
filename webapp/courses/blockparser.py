# -*- coding: utf-8 -*-
"""Parser for inline wiki markup tags that appear in paragraphs, tables etc."""

import re

import pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from django.utils.text import slugify

import courses.models
import courses.markupparser

from utils.parsing import BrokenLinkWarning, parse_link_url


class Tag:
    """One markup tag type."""

    def __init__(self, tagname, tagbegin, tagend, tagre):
        self.name = tagname
        self.begin = tagbegin
        self.end = tagend
        self.re = tagre
        self.options = None

    def set_options(self, options):
        self.options = options

    def htmlbegin(self, options=None):
        """Returns the HTML equivalent begin tag of the inline wiki markup."""
        if not self.options and not options:
            return f"<{self.name}>"

        if self.options and not options:
            option_string = " ".join(f'{key}="{value}"' for key, value in self.options.items())
        elif not self.options and options:
            option_string = " ".join(f'{key}="{value}"' for key, value in options.items())
        else:
            option_string = " ".join(
                f'{key}="{value}"'
                for key, value in dict(self.options.items() + options.items()).items()
            )
        return f"<{self.name} {option_string}>"

    def htmlend(self):
        """Returns the HTML equivalent end tag."""
        return f"</{self.name}>"

    def lb(self):
        """Length of the beginning wiki markup tag."""
        return len(self.begin)

    def le(self):
        """Length of the ending wiki markup tag."""
        return len(self.end)


# A library of different tags supported by the wiki markup
tags = {
    "bold": Tag(
        "strong",
        "'''",
        "'''",
        re.compile(r"[']{3}(?P<bold_italic>[']{2})?.+?(?P=bold_italic)?[']{3}"),
    ),
    "italic": Tag("em", "''", "''", re.compile(r"[']{2}.+?[']{2}")),
    "pre": Tag("code", "{{{", "}}}", re.compile(r"[{]{3}(?P<highlight>\#\![^\s]+ )?.+?[}]{3}")),
    "dfn": Tag("dfn", "", "", re.compile(r"")),
    "mark": Tag("mark", "!!!", "!!!", re.compile(r"[\!]{3}.+?[\!]{3}")),
    "anchor": Tag("a", "[[", "]]", re.compile(r"\[\[(?P<address>.+?)([|](?P<link_text>.+?))?\]\]")),
    "kbd": Tag("kbd", "`", "`", re.compile(r"`(?P<kbd>.+?)`")),
    "hint": Tag(
        "mark",
        "[!hint=hint_id!]",
        "[!hint!]",
        re.compile(r"\[\!hint\=(?P<hint_id>[^!]+)\!\](?P<hint_text>.+?)\[\!hint\!\]"),
    ),
    "term": Tag(
        "div",
        "[!term=term_name!]",
        "[!term!]",
        re.compile(r"\[\!term\=(?P<term_name>[^!]+)\!\](?P<term_text>.+?)\[\!term\!\]"),
    ),
    "dl": Tag(
        "span",
        "[!dl=page_slug!]",
        "[!dl!]",
        re.compile(r"\[\!dl\=(?P<page_slug>[^!]+)\!\]"),
    ),
    "thold": Tag(
        "span",
        "[!threshold=grade!]",
        "[!threshold!]",
        re.compile(r"\[\!threshold\=(?P<grade>[^!]+)\!\]"),
    ),
    "color": Tag(
        "span",
        "[!color=value!]",
        "[!color!]",
        re.compile(r"\[\!color\=(?P<color>[^!]+)\!\](?P<colored_text>.+?)\[\!color\!\]"),
    )
}


def parse_pre_tag(parsed_string, tag, hilite, match):
    code_string = match.group(0)[tag.lb() + len(hilite) : -tag.le()]
    for escaped, unescaped in {"&lt;": "<", "&gt;": ">", "&amp;": "&"}.items():
        code_string = code_string.replace(escaped, unescaped)
    hilite = hilite.strip("#! ")

    parsed_string += tag.htmlbegin({"class": "highlight " + hilite})
    try:
        lexer = get_lexer_by_name(hilite)
    except pygments.util.ClassNotFound as e:
        parsed_string += f"no such highlighter: {hilite}; "
        parsed_string += code_string
    else:
        parsed_string += highlight(code_string, lexer, HtmlFormatter(nowrap=True)).rstrip("\n")
    parsed_string += tag.htmlend()

    return parsed_string


def parse_anchor_tag(parsed_string, tag, address, link_text, context):
    try:
        final_address, target = parse_link_url(address, context)
    except BrokenLinkWarning:
        final_address = ""
        target = "_self"
        parsed_string += "<span>-- WARNING: BROKEN LINK --</span>"

    parsed_string += tag.htmlbegin(
        {
            "href": final_address,
            "target": target,
        }
    )
    parsed_string += link_text or address
    parsed_string += tag.htmlend()

    return parsed_string


def parse_hint_tag(parsed_string, tag, hint_id, hint_text):
    parsed_string += tag.htmlbegin({"class": "hint-inactive", "id": "hint-id-" + hint_id})
    parsed_string += hint_text
    parsed_string += tag.htmlend()
    return parsed_string


def parse_term_tag(parsed_string, tag, term_name, term_text, context):
    if context is not None and "tooltip" in context and context["tooltip"]:
        parsed_string += term_text
        return parsed_string

    if context is not None and context.get("instance") is None:
        parsed_string += f'<span class="term">{term_text}</span>'
        return parsed_string

    div_id = f"#{slugify(term_name, allow_unicode=True)}-term-div"
    on_mouse_enter = f"show_term_description_during_hover(this, event, '{div_id}');"
    on_mouse_leave = f"hide_tooltip('{div_id}');"

    parsed_string += tag.htmlbegin(
        {
            "class": "term-container",
            "onmouseenter": on_mouse_enter,
            "onmouseleave": on_mouse_leave,
        }
    )
    parsed_string += f'<span class="term">{term_text}</span>'
    parsed_string += tag.htmlend()
    return parsed_string


def parse_dl_tag(parsed_string, tag, page_slug, context):
    parsed_string += tag.htmlbegin({"class": "date-display"})
    try:
        parsed_string += courses.models.ContentGraph.objects.get(
            content__slug=page_slug, instance=context.get("instance", None)
        ).deadline.strftime("%Y-%m-%d %H:%M")
    except AttributeError:
        parsed_string += ""
    except courses.models.ContentGraph.DoesNotExist:
        parsed_string += "-- WARNING: BROKEN REFERENCE --"
    parsed_string += tag.htmlend()
    return parsed_string


def parse_threshold_tag(parsed_string, tag, grade, context):
    parsed_string += tag.htmlbegin({"class": "grade-threshold-display"})
    try:
        parsed_string += str(
            courses.models.GradeThreshold.objects.get(
                instance=context.get("instance", None), grade=grade
            ).threshold
        )
    except courses.models.GradeThreshold.DoesNotExist:
        parsed_string += "-- WARNING: BROKEN REFERENCE --"
    parsed_string += tag.htmlend()
    return parsed_string


def parse_color_tag(parsed_string, tag, color, text):
    parsed_string += tag.htmlbegin({"style": f"color: {color}"})
    parsed_string += text
    parsed_string += tag.htmlend()
    return parsed_string



def parsetag(tagname, unparsed_string, context=None):
    """Parses one tag and applies it's settings. Generates the HTML."""
    tag = tags[tagname]
    hilite = (
        address
    ) = link_text = hint_id = hint_text = term_name = term_text = page_slug = grade = color = None
    parsed_string = ""
    cursor = 0
    for m in re.finditer(tag.re, unparsed_string):
        parsed_string += unparsed_string[cursor : m.start()]

        # Get code
        try:
            hilite = m.group("highlight")
        except IndexError:
            pass

        # Get anchor
        try:
            address = m.group("address")
            link_text = m.group("link_text")
        except IndexError:
            pass

        # Get hint
        try:
            hint_id = m.group("hint_id")
            hint_text = m.group("hint_text")
        except IndexError:
            pass

        try:
            term_name = m.group("term_name")
            term_text = m.group("term_text")
        except IndexError:
            pass

        try:
            page_slug = m.group("page_slug")
        except IndexError:
            pass

        try:
            grade = m.group("grade")
        except IndexError:
            pass

        try:
            color = m.group("color")
            text = m.group("colored_text")
        except IndexError:
            pass

        if hilite:
            parsed_string = parse_pre_tag(parsed_string, tag, hilite, m)
        elif address:
            parsed_string = parse_anchor_tag(parsed_string, tag, address, link_text, context)
        elif hint_id:
            parsed_string = parse_hint_tag(parsed_string, tag, hint_id, hint_text)
        elif term_name:
            parsed_string = parse_term_tag(parsed_string, tag, term_name, term_text, context)
        elif page_slug:
            parsed_string = parse_dl_tag(parsed_string, tag, page_slug, context)
        elif grade:
            parsed_string = parse_threshold_tag(parsed_string, tag, grade, context)
        elif color:
            parsed_string = parse_color_tag(parsed_string, tag, color, text)
        else:
            contents = m.group(0)[tag.lb() : -tag.le()]

            if tagname == "kbd":
                key_mini_lang = {
                    "{apple}": " Apple",
                    "{arrowdown}": "↓",
                    "{arrowleft}": "←",
                    "{arrowright}": "→",
                    "{arrowup}": "↑",
                    "{enter}": "↵ Enter",
                    "{cmd}": "⌘ Command",
                    "{meta}": "◆ Meta",
                    "{option}": "⌥ Option",
                    "{shift}": "⇧ Shift",
                    "{win}": "⊞ Win",
                }
                contents = key_mini_lang.get(contents, contents)

            parsed_string += tag.htmlbegin()
            parsed_string += contents
            parsed_string += tag.htmlend()

        cursor = m.end()
        hilite = False
    parsed_string += unparsed_string[cursor:]

    return parsed_string


def parseblock(blockstring, context=None):
    """A multi-pass parser for inline markup language inside paragraphs."""

    parsed_string = parsetag("pre", blockstring)
    parsed_string = parsetag("bold", parsed_string)
    parsed_string = parsetag("italic", parsed_string)
    parsed_string = parsetag("mark", parsed_string)
    parsed_string = parsetag("kbd", parsed_string)
    parsed_string = parsetag("anchor", parsed_string, context)
    parsed_string = parsetag("hint", parsed_string)
    parsed_string = parsetag("term", parsed_string, context)
    parsed_string = parsetag("dl", parsed_string, context)
    parsed_string = parsetag("thold", parsed_string, context)
    parsed_string = parsetag("color", parsed_string, context)
    return parsed_string


# Some test code
if __name__ == "__main__":
    block_1 = "'''alku on boldia ''ja valissa on italistoitua'' ja sitten jatkuu boldi'''"
    block_2 = (
        "alku ei ole boldia '''''mutta sitte tulee itaboldi kohta'' "
        "joka jatkuu boldina''' ja loppuu epaboldina"
    )
    block_3 = (
        "normi '''bold''' normi '''bold''' normi ''italic'' normi "
        "'''bold''' normi ''italic'' '''bold''' normi"
    )
    block_4 = "one '''doesn't''' simply walk into mordor"
    block_5 = "jeejee ''ita'''itabold'''''"

    blocks = [block_1, block_2, block_3, block_4, block_5]

    for i, block in enumerate(blocks):
        print(f"Test {i:02}:")
        parseblock(block)
        print()
