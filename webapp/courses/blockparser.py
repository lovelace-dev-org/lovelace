# -*- coding: utf-8 -*-
"""Parser for inline wiki markup tags that appear in paragraphs, tables etc."""

import re

class Tag:
    """One markup tag type."""

    def __init__(self):
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

    def render_tag(self, match, context):
        parsed_string = self.htmlbegin()
        parsed_string += match.group(0)[self.lb() : -self.le()]
        parsed_string += self.htmlend()
        return parsed_string

    def parse(self, unparsed_string, context):
        parsed_string = ""
        cursor = 0
        for match in re.finditer(self.regexp, unparsed_string):
            parsed_string += unparsed_string[cursor:match.start()]
            parsed_string += self.render_tag(match, context)
            cursor = match.end()

        parsed_string += unparsed_string[cursor:]
        return parsed_string


class BlockParser:

    tags = {}

    @classmethod
    def register_tag(cls, handle, tag_cls):
        cls.tags[handle] = tag_cls()

    def parse_block(self, blockstring, context=None):
        for tag in self.tags.values():
            blockstring = tag.parse(blockstring, context)

        return blockstring


def parseblock(blockstring, context=None):
    parser = BlockParser()
    return parser.parse_block(blockstring, context)
