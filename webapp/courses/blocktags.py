import re

import pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from django.utils.text import slugify

import courses.models as cm
from courses.blockparser import Tag, BlockParser
from utils.parsing import BrokenLinkWarning, parse_link_url


class BoldTag(Tag):

    name = "strong"
    begin = "'''"
    end = "'''"
    regexp = re.compile(r"[']{3}(?P<bold_italic>[']{2})?.+?(?P=bold_italic)?[']{3}")


class ItalicTag(Tag):

    name = "em"
    begin = "''"
    end = "''"
    regexp = re.compile(r"[']{2}.+?[']{2}")


class PreTag(Tag):

    name = "code"
    begin = "{{{"
    end = "}}}"
    regexp = re.compile(r"[{]{3}(?P<highlight>\#\![^\s]+ )?.+?[}]{3}")

    def render_tag(self, match, context):
        hilite = match.group("highlight") or ""
        code_string = match.group(0)[self.lb() + len(hilite) : -self.le()]
        for escaped, unescaped in {"&lt;": "<", "&gt;": ">", "&amp;": "&"}.items():
            code_string = code_string.replace(escaped, unescaped)
        hilite = hilite.strip("#! ")

        parsed_string = self.htmlbegin({"class": "highlight " + hilite})
        try:
            lexer = get_lexer_by_name(hilite)
        except pygments.util.ClassNotFound as e:
            parsed_string += f"no such highlighter: {hilite}; "
            parsed_string += code_string
        else:
            parsed_string += highlight(code_string, lexer, HtmlFormatter(nowrap=True)).rstrip("\n")

        parsed_string += self.htmlend()
        return parsed_string


class MarkTag(Tag):

    name = "mark"
    begin = "!!!"
    end = "!!!"
    regexp = re.compile(r"[\!]{3}.+?[\!]{3}")


class AnchorTag(Tag):

    name = "a"
    begin = "[["
    end = "]]"
    regexp = re.compile(r"\[\[(?P<address>.+?)([|](?P<link_text>.+?))?\]\]")

    def render_tag(self, match, context):
        address = match.group("address")
        link_text = match.group("link_text")
        try:
            final_address, target = parse_link_url(address, context)
        except BrokenLinkWarning:
            final_address = ""
            target = "_self"
            return "<span>-- WARNING: BROKEN LINK --</span>"

        parsed_string = self.htmlbegin(
            {
                "href": final_address,
                "target": target,
            }
        )
        parsed_string += link_text or address
        parsed_string += self.htmlend()
        return parsed_string


class KeyboardTag(Tag):

    name = "kbd"
    begin = "`"
    end = "`"
    regexp = re.compile(r"`(?P<kbd>.+?)`")

    def render_tag(self, match, context):
        symbol = match.group("kbd")
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
        return key_mini_lang.get(symbol, symbol)


class ColorTag(Tag):

    name = "span"
    begin = "[!color=value!]"
    end = "[!color!]"
    regexp = re.compile(r"\[\!color\=(?P<color>[^!]+)\!\](?P<colored_text>.+?)\[\!color\!\]")

    def render_tag(self, match, context):
        color = match.group("color")
        text = match.group("colored_text")
        parsed_string = self.htmlbegin({"style": f"color: {color}"})
        parsed_string += text
        parsed_string += self.htmlend()
        return parsed_string


class HintTag(Tag):

    name = "mark"
    begin = "[!hint=hint_id!]"
    end = "[!hint!]"
    regexp = re.compile(r"\[\!hint\=(?P<hint_id>[^!]+)\!\](?P<hint_text>.+?)\[\!hint\!\]")

    def render_tag(self, match, context):
        parsed_string = self.htmlbegin({
            "class": "hint-inactive",
            "id": "hint-id-" + match.group("hint_id")
        })
        parsed_string += match.group("hint_text")
        parsed_string += self.htmlend()
        return parsed_string


class TermTag(Tag):

    name = "div"
    begin = "[!term=term_name!]"
    end = "[!term!]"
    regexp = re.compile(r"\[\!term\=(?P<term_name>[^!]+)\!\](?P<term_text>.+?)\[\!term\!\]")

    def render_tag(self, match, context):
        term_name = match.group("term_name")
        term_text = match.group("term_text")
        if context is not None and "tooltip" in context and context["tooltip"]:
            parsed_string = term_text
            return parsed_string

        if context is not None and context.get("instance") is None:
            parsed_string = f'<span class="term">{term_text}</span>'
            return parsed_string

        div_id = f"#{slugify(term_name, allow_unicode=True)}-term-div"
        on_mouse_enter = f"show_term_description_during_hover(this, event, '{div_id}');"
        on_mouse_leave = f"hide_tooltip('{div_id}');"

        parsed_string = self.htmlbegin(
            {
                "class": "term-container",
                "onmouseenter": on_mouse_enter,
                "onmouseleave": on_mouse_leave,
            }
        )
        parsed_string += f'<span class="term">{term_text}</span>'
        parsed_string += self.htmlend()
        return parsed_string


class DeadlineTag(Tag):

    name = "span"
    begin = "[!dl=page_slug!]"
    end = "[!dl]"
    regexp = re.compile(r"\[\!dl\=(?P<page_slug>[^!]+)\!\]")

    def render_tag(self, match, context):
        parsed_string = self.htmlbegin({"class": "date-display"})
        page_slug = match.group("page_slug")
        try:
            parsed_string += cm.ContentGraph.objects.get(
                content__slug=page_slug, instance=context.get("instance", None)
            ).deadline.strftime("%Y-%m-%d %H:%M")
        except AttributeError:
            parsed_string += ""
        except cm.ContentGraph.DoesNotExist:
            parsed_string += "-- WARNING: BROKEN REFERENCE --"
        parsed_string += self.htmlend()
        return parsed_string


class GradeThresholdTag(Tag):

    name = "span"
    begin = "[!threshold=grade!]"
    end = "[!threshold!]"
    regexp = re.compile(r"\[\!threshold\=(?P<grade>[^!]+)\!\]")

    def render_tag(self, match, context):
        grade = match.group("grade")
        parsed_string = self.htmlbegin({"class": "grade-threshold-display"})
        try:
            parsed_string += str(
                cm.GradeThreshold.objects.get(
                    instance=context.get("instance", None), grade=grade
                ).threshold
            )
        except cm.GradeThreshold.DoesNotExist:
            parsed_string += "-- WARNING: BROKEN REFERENCE --"
        parsed_string += self.htmlend()
        return parsed_string




def register_tags():
    BlockParser.register_tag("pre", PreTag)
    BlockParser.register_tag("bold", BoldTag)
    BlockParser.register_tag("italic", ItalicTag)
    BlockParser.register_tag("mark", MarkTag)
    BlockParser.register_tag("anchor", AnchorTag)
    BlockParser.register_tag("kbd", KeyboardTag)
    BlockParser.register_tag("color", ColorTag)
    BlockParser.register_tag("hint", HintTag)
    BlockParser.register_tag("term", TermTag)
    BlockParser.register_tag("dl", DeadlineTag)
    BlockParser.register_tag("thold", GradeThresholdTag)


