# -*- coding: utf-8 -*-
"""
Parser for wiki markup block content, i.e. paragraphs, bullet lists, tables, etc.
Idea from http://wiki.sheep.art.pl/Wiki%20Markup%20Parser%20in%20Python
"""

import re
import os
import codecs
import itertools
#from django.utils.html import escape # Not good, escapes ' characters which prevents syntax parsing
from cgi import escape # Use this instead

from pygments import highlight
from pygments.lexers import PythonLexer, CLexer
from pygments.formatters import HtmlFormatter

from courses.highlighters import highlighters

import courses.blockparser as blockparser

class ContentParser:
    """Parser class for generating HTML from wiki markup block types."""
    
    # Generates a regular expression from the supported block types
    block = {
        "bullet" : r"^\s*(?P<ulist_level>[*]+)\s+",
        "ordered_list" : r"^\s*(?P<olist_level>[#]+)\s+",
        "separator" : r"^\s*[-]{2}\s*$",
        "image" : r"^[{]{2}image\:(?P<imagename>[^|]+)(\|(?P<alt>.+))?[}]{2}$",
        "calendar" : r"^[{]{2}calendar\:(?P<calendarname>.+)[}]{2}$",
        "video" : r"^[{]{2}video\:(?P<videoname>.+)[}]{2}$",
        "codefile" : r"[{]{3}\!(?P<filename>[^\s]+)\s*[}]{3}$",
        "code" : r"^[{]{3}(\#\!(?P<highlight>%s))?\s*$" % ("|".join(highlighters.keys())),
        "taskembed" : r"^\[\[\[(?P<taskname>[^\s]+)\]\]\]$",
        "table" : r"^([|]{2}[^|]*)+[|]{2}$",
        "empty" : r"^\s*$",
        "heading" : r"^\s*(?P<len>[=]{1,6})[=]*\s*.+\s*(?P=len)\s*$",
        #"indent" : r"^[ \t]+", # Indents are not supported
    }
    block_re = re.compile(r"|".join(r"(?P<%s>%s)" % kv for kv in sorted(block.items())))

    def __init__(self, lines=None):        
        self.lines = lines             # The lines of the markup text that's going to get parsed
        self.current_filename = None   # If we've found a file name that has to be stored
        self.current_taskname = None   # If we've found an embedded task page name that has to be stored
        self.current_videoname = None  # If we've found an embedded video name that has to be stored
        self.current_imagename = None  # If we've found an embedded picture name that has to be stored
        self.current_calendarname = None # Same but for embedded calendars
        self.list_state = []           # For the stateful ul-ol-tag representation
        self.in_table = False          # If we are currently inside a table
        self.table_header_used = False # If th tag equivalent was used
    
    def get_line_kind(self, line):
        matchobj = self.block_re.match(line)
        return getattr(matchobj, "lastgroup", u"paragraph"), matchobj
    
    def block_heading(self, block, settings):
        yield u"<h%d>" % settings["heading_size"]
        for line in block:
            yield escape(line.strip("= \r\n\t"))
        yield u'</h%d>\n' % settings["heading_size"]
    def settings_heading(self, matchobj):
        heading_size = len(matchobj.group("len"))
        
        settings = {"heading_size" : heading_size}
        return settings
    
    def block_paragraph(self, block, settings):
        yield u'<p>'
        paragraph = u""
        paragraph_lines = []
        for line in block:
            paragraph_lines.append(escape(line))
        paragraph = u"<br />".join(paragraph_lines)
        paragraph = blockparser.parseblock(paragraph)
        yield paragraph
        yield u'</p>\n'
    def settings_paragraph(self, matchobj):
        pass
    
    def block_empty(self, block, settings):
        yield u''
    def settings_empty(self, matchobj):
        pass

    def block_separator(self, block, settings):
        yield u'<hr />'
    def settings_separator(self, matchobj):
        pass
    
    def block_bullet(self, block, settings):
        if len(self.list_state) < settings["list_level"]:
            for new_lvl in range(settings["list_level"] - len(self.list_state)):
                self.list_state.append("ul")
                yield u'<ul>'
        elif len(self.list_state) > settings["list_level"]:
            for new_lvl in range(len(self.list_state) - settings["list_level"]):
                top_lvl = self.list_state.pop()
                yield u'</%s>' % top_lvl
        if len(self.list_state) == settings["list_level"]:
            if self.list_state[-1] == "ol":
                top_lvl = self.list_state.pop()
                yield u'</ol>'
                self.list_state.append("ul")
                yield u'<ul>'
        for line in block:
            yield '<li>%s</li>' % (blockparser.parseblock(escape(line.strip("* \r\n\t"))))
    def settings_bullet(self, matchobj):
        list_level = len(matchobj.group("ulist_level"))
        settings = {"list_level" : list_level}
        return settings

    def block_ordered_list(self, block, settings):
        if len(self.list_state) < settings["list_level"]:
            for new_lvl in range(settings["list_level"] - len(self.list_state)):
                self.list_state.append("ol")
                yield u'<ol>'
            #self.list_level = settings["list_level"]
        elif len(self.list_state) > settings["list_level"]:
            for new_lvl in range(len(self.list_state) - settings["list_level"]):
                top_lvl = self.list_state.pop()
                yield u'</%s>' % top_lvl
            #self.list_level = settings["list_level"]
        if len(self.list_state) == settings["list_level"]:
            if self.list_state[-1] == "ul":
                top_lvl = self.list_state.pop()
                yield u'</ul>'
                self.list_state.append("ol")
                yield u'<ol>'
        for line in block:
            yield '<li>%s</li>' % (blockparser.parseblock(escape(line.strip("# \r\n\t"))))
    def settings_ordered_list(self, matchobj):
        list_level = len(matchobj.group("olist_level"))
        settings = {"list_level" : list_level}
        return settings

    def block_image(self, block, settings):
        if settings["alt"]:
            yield u'<img src="%s" alt="%s" />' % (settings["imageurl"], settings["alt"])
        else:
            yield u'<img src="%s" />' % (settings["imageurl"])
    def settings_image(self, matchobj):
        imagename = escape(matchobj.group("imagename"))
        #imageurl = "%s%s/%s" % (self.mediaurl, self.coursename, imagename)
        imageurl = "{{ %s }}" % (imagename)
        self.current_imagename = imagename
        alt = u""
        try:
            alt = escape(matchobj.group("alt"))
        except AttributeError:
            pass

        settings = {"imagename" : imagename, "alt" : alt, "imageurl" : imageurl}
        return settings

    def block_calendar(self, block, settings):
        yield '<div class="calendar">'
        yield '{{ %s }}' % settings["calendarname"]
        yield '</div>'
    def settings_calendar(self, matchobj):
        calendarname = escape(matchobj.group("calendarname"))
        self.current_calendarname = calendarname

        settings = {"calendarname" : calendarname}
        return settings

    def block_video(self, block, settings):
        # No <video> tag support yet
        #yield u'<video src="%s">Your browsers doesn\'t support videos!</video>' % (settings["videoname"])
        self.current_videoname = settings["videoname"]
        yield u'<iframe width="560" height="315" src="{{ %s }}" frameborder="0" allowfullscreen></iframe>' % (settings["videoname"])
    def settings_video(self, matchobj):
        videoname = escape(matchobj.group("videoname"))
        
        settings = {"videoname" : videoname}
        return settings

    def block_codefile(self, block, settings):
        fp = os.path.join(self.fileroot, "courses")
        fpb = os.path.join(fp, "codefile-normal-begin.html")
        fpe = os.path.join(fp, "codefile-normal-end.html")
        codefile_normal_begin = codecs.open(fpb, "r", "utf-8").read().strip()
        codefile_normal_begin = codefile_normal_begin.replace("{{ filename }}", settings["filename"])
        codefile_normal_begin = codefile_normal_begin.replace("{{ fileurl }}",  settings["fileurl"])
        codefile_normal_end = codecs.open(fpe, "r", "utf-8").read().strip()
        self.current_filename = settings["filename"]
        for part in block:
            yield codefile_normal_begin
            yield '{{ %s }}' % settings["filename"]  # TODO: Output the file here instead of in the view.
            yield codefile_normal_end
    def settings_codefile(self, matchobj):
        filename = escape(matchobj.group("filename"))
        fileurl = "%sfiles/%s" % (self.mediaurl, filename)
 
        settings = {"filename" : filename, "fileurl" : fileurl}
        return settings

    def block_code(self, block, settings):
        for part in block:
            yield u'<pre class="normal">'
            if settings["highlight"]:
                yield u'<code class="%s">' % ("highlight-" + settings["highlight"])
                lines = []
                try:
                    line = self.lines.next()
                    print(settings["highlight"])
                    while not line.startswith("}}}"):
                        lines.append(line)
                        line = self.lines.next()
                except StopIteration:
                    lines.append(u'Warning: unclosed code block!\n')
                code_string = u"\n".join(lines)
                highlighted = highlight(code_string, highlighters[settings["highlight"]](), HtmlFormatter(nowrap=True))
                yield highlighted
                yield u'</code>'
            else:
                try:
                    line = self.lines.next()
                    while not line.startswith("}}}"):
                        yield escape(line) + "\n"
                        line = self.lines.next()
                except StopIteration:
                    yield u'Warning: unclosed code block!\n'
            yield u'</pre>\n'
    def settings_code(self, matchobj):
        highlight = matchobj.group("highlight")
        
        settings = {"highlight" : highlight,}
        return settings

    def block_taskembed(self, block, settings):
        self.current_taskname = settings["taskname"]
        yield '<div class="embedded_task">'
        yield '{{ %s }}' % settings["taskname"]
        yield '</div>'
    def settings_taskembed(self, matchobj):
        taskname = escape(matchobj.group("taskname"))

        settings = {"taskname" : taskname}
        return settings

    def block_table(self, block, settings):
        if not self.in_table:
            self.in_table = True
            yield u'<table>'
        if not self.table_header_used and settings["thead"]:
            yield u'<thead>'
        yield u'<tr>'
        for i, cell in enumerate(settings["cells"]):
            if settings["thcells"][i]:
                yield u'<th>%s</th>' % cell
            else:
                yield u'<td>%s</td>' % blockparser.parseblock(cell)
        yield u'</tr>'
        if not self.table_header_used and settings["thead"]:
            self.table_header_used = True
            yield u'</thead>'
    def settings_table(self, matchobj):
        cells = matchobj.group(0).strip().split("||")
        cells.pop() # Remove the entry after last ||
        cells.pop(0) # Remove the entry before first ||
        thcells = [cell.startswith("!") for cell in cells]
        cells = [escape(cell.lstrip("!")) for cell in cells]
        thead = False not in thcells
        
        settings = {"cells" : cells,
                    "thcells" : thcells,
                    "thead" : thead,}
        return settings

    def set_fileroot(self, fileroot):
        self.fileroot = fileroot
    def set_mediaurl(self, mediaurl):
        self.mediaurl = mediaurl
    def set_coursename(self, coursename):
        self.coursename = coursename

    def get_current_filename(self):
        return self.current_filename
    def get_current_taskname(self):
        return self.current_taskname
    def get_current_videoname(self):
        return self.current_videoname
    def get_current_imagename(self):
        return self.current_imagename
    def get_current_calendarname(self):
        return self.current_calendarname
        
    def parse(self):
        for group_info, block in itertools.groupby(self.lines, self.get_line_kind):
            func = getattr(self, "block_%s" % group_info[0])
            settings = getattr(self, "settings_%s" % group_info[0])(group_info[1])

            # Reset list settings
            if group_info[0] != "bullet" and group_info[0] != "ordered_list":
                for undent_lvl in range(len(self.list_state)):
                    top_lvl = self.list_state.pop()
                    yield u'</%s>' % top_lvl

            # Reset table settings
            if group_info[0] != 'table' and self.in_table:
                self.in_table = False
                self.table_header_used = False
                yield u'</table>'

            #print block, settings
            for part in func(block, settings):
                yield part

        # Close remaining tags when the end of the page has been reached
        for remaining_lvl in reversed(self.list_state): # Clean up possible list indentations
            yield u'</%s>' % remaining_lvl
        if self.in_table: # Clean up possible open tables
            yield u'</table>'


# Test code
if __name__ == "__main__":
    test_file = open("test1.txt")
    
    test = ContentParser(test_file)
    html = u""
    for line in test.parse():
        html += line
    
    print(html)
