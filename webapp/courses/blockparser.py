# -*- coding: utf-8 -*-
"""Parser for inline wiki markup tags that appear in paragraphs, tables etc."""

import re
import courses.models
# TODO: {{{#!python {}}}} breaks up!
# TODO: |forcedownload or |forceview for links
import pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_all_lexers
from pygments.formatters import HtmlFormatter

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
            return "<%s>" % (self.name)
        elif self.options and not options:
            return "<%s %s>" % (self.name, " ".join("%s=\"%s\"" % kv for kv in self.options.items()))
        elif not self.options and options:
            return "<%s %s>" % (self.name, " ".join("%s=\"%s\"" % kv for kv in options.items()))
        else:
            return "<%s %s>" % (self.name, " ".join("%s=\"%s\"" % kv for kv in dict(self.options.items() + options.items()).items()))
    
    def htmlend(self):
        """Returns the HTML equivalent end tag."""
        return "</%s>" % (self.name)

    def lb(self):
        """Length of the beginning wiki markup tag."""
        return len(self.begin)
    def le(self):
        """Length of the ending wiki markup tag."""
        return len(self.end)

# A library of different tags supported by the wiki markup
tags = {
    "bold":   Tag("strong", "'''", "'''", re.compile(r"[']{3}(?P<bold_italic>[']{2})?.+?(?P=bold_italic)?[']{3}")),
    "italic": Tag("em", "''", "''", re.compile(r"[']{2}.+?[']{2}")),
    "pre":    Tag("code", "{{{", "}}}", re.compile(r"[{]{3}(?P<highlight>\#\![^\s]+ )?.+?[}]{3}")),
    "dfn":    Tag("dfn", "", "", re.compile(r"")),
    "mark":   Tag("mark", "!!!", "!!!", re.compile(r"[\!]{3}.+?[\!]{3}")),
    "anchor": Tag("a", "[[", "]]", re.compile(r"\[\[(?P<address>.+?)([|](?P<link_text>.+?))?\]\]")),
    "kbd":    Tag("kbd", "`", "`", re.compile(r"`(?P<kbd>.+?)`")),
    "hint":   Tag("mark", "[!hint=hint_id!]", "[!hint!]", re.compile(r"\[\!hint\=(?P<hint_id>\w+)\!\](?P<hint_text>.+?)\[\!hint\!\]")),
    "term":   Tag("span", '"""', '"""', re.compile(r"\"{3}(?P<term>.+?)\"{3}")),
}

def parsetag(tagname, unparsed_string, context=None):
    """Parses one tag and applies it's settings. Generates the HTML."""
    tag = tags[tagname]
    hilite = address = link_text = hint_id = hint_text = term = None
    parsed_string = ""
    cursor = 0
    for m in re.finditer(tag.re, unparsed_string):
        parsed_string += unparsed_string[cursor:m.start()]

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
            term = m.group("term")
        except IndexError:
            pass
        
        if hilite:
            code_string = m.group(0)[tag.lb()+len(hilite):-tag.le()]
            for escaped, unescaped in {"&lt;":"<", "&gt;":">", "&amp;":"&"}.items():
                code_string = code_string.replace(escaped, unescaped)
            hilite = hilite.strip("#! ")
            parsed_string += tag.htmlbegin({"class":"highlight " + hilite})
            try:
                lexer = get_lexer_by_name(hilite)
            except pygments.util.ClassNotFound as e:
                parsed_string += "no such highlighter: %s; " % hilite
                parsed_string += code_string
            else:    
                parsed_string += highlight(code_string, lexer, HtmlFormatter(nowrap=True)).rstrip("\n")
            parsed_string += tag.htmlend()
        elif address:
            contents = link_text or address
            parsed_string += tag.htmlbegin({"href":address, "target":"_blank"})
            parsed_string += contents
            parsed_string += tag.htmlend()
            #print tag.htmlbegin({"href":address}) + contents + tag.htmlend()
        elif hint_id:
            parsed_string += tag.htmlbegin({"class":"hint", "id":"hint-id-"+hint_id})
            parsed_string += hint_text
            parsed_string += tag.htmlend()
        elif term:
            description = "?"
            if context is not None:
                try:
                    course = context["course"]
                except KeyError:
                    pass
                else:
                    try:
                        description = courses.models.Term.objects.get(name=term, instance__course=course).description
                    except courses.models.Term.DoesNotExist as e:
                        pass
            parsed_string += tag.htmlbegin({"class":"term", "title":description})
            parsed_string += term
            parsed_string += tag.htmlend()
        else:
            contents = m.group(0)[tag.lb():-tag.le()]

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
    # TODO: Start with pre tags to prevent formatting inside pre
    #       - Perhaps use a state machine to determine, whether inside pre
    #if len(re.findall("'''", blockstring)) % 2:
        # TODO: Raise an exception instead, show the exception at the end of the block in red
        #return blockstring

    parsed_string = parsetag("pre", blockstring)
    parsed_string = parsetag("bold", parsed_string)
    parsed_string = parsetag("italic", parsed_string)
    parsed_string = parsetag("mark", parsed_string)
    parsed_string = parsetag("kbd", parsed_string)
    parsed_string = parsetag("anchor", parsed_string)
    parsed_string = parsetag("hint", parsed_string)
    parsed_string = parsetag("term", parsed_string, context)

    return parsed_string

# Some test code
if __name__ == "__main__":
    block1 = "'''alku on boldia ''ja valissa on italistoitua'' ja sitten jatkuu boldi'''"
    block2 = "alku ei ole boldia '''''mutta sitte tulee itaboldi kohta'' joka jatkuu boldina''' ja loppuu epaboldina"
    block3 = "normi '''bold''' normi '''bold''' normi ''italic'' normi '''bold''' normi ''italic'' '''bold''' normi"
    block4 = "one '''doesn't''' simply walk into mordor"
    block5 = "jeejee ''ita'''itabold'''''"

    blocks = [block1, block2, block3, block4, block5]

    for i, block in enumerate(blocks):
        print("Test %02d:" % i)
        parseblock(block)
        print()
