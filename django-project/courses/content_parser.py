# -*- coding: utf-8 -*-
# http://wiki.sheep.art.pl/Wiki%20Markup%20Parser%20in%20Python

import re
import itertools
from django.utils.html import escape

class ContentParser(object):
    block = {
        "bullet" : ur"^\s*(?P<ulist_level>[*]+)\s+",
        "ordered_list" : ur"^\s*(?P<olist_level>[#]+)\s+",
        "separator" : ur"^\s*[-]{2}\s*$",
        "codefile" : ur"[{]{3}\!(?P<filename>[^\s]+)\s*[}]{3}$",
        "code" : ur"^[{]{3}\s*$",
        "taskembed" : ur"^\[\[\[(?P<taskname>[^\s]+)\]\]\]$",
        "table" : ur"^([|]{2}[^|]*)+[|]{2}$",
        "empty" : ur"^\s*$",
        "heading" : ur"^\s*(?P<len>[=]{1,6})[=]*\s*.+\s*(?P=len)\s*$",
        "indent" : ur"^[ \t]+",
    }
    block_re = re.compile(ur"|".join("(?P<%s>%s)" % kv for kv in sorted(block.iteritems())))

    def __init__(self, lines=None):
        """asdf
        
        asdf
        """
        
        self.lines = lines
        self.current_filename = None
        self.current_taskname = None
        self.list_state = []
        self.in_table = False
        self.table_header_used = False
    
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
        for line in block:
            yield escape(line)
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
            #self.list_level = settings["list_level"]
        elif len(self.list_state) > settings["list_level"]:
            for new_lvl in range(len(self.list_state) - settings["list_level"]):
                top_lvl = self.list_state.pop()
                yield u'</%s>' % top_lvl
            #self.list_level = settings["list_level"]
        if len(self.list_state) == settings["list_level"]:
            if self.list_state[-1] == "ol":
                top_lvl = self.list_state.pop()
                yield u'</ol>'
                self.list_state.append("ul")
                yield u'<ul>'
        for line in block:
            yield '<li>%s</li>' % (escape(line.strip("* \r\n\t")))
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
            yield '<li>%s</li>' % (escape(line.strip("# \r\n\t")))
    def settings_ordered_list(self, matchobj):
        list_level = len(matchobj.group("olist_level"))
        settings = {"list_level" : list_level}
        return settings

    def block_codefile(self, block, settings):
        import codecs
        codefile_normal_begin = codecs.open("courses/codefile-normal-begin.html", "r", "utf-8").read().strip()
        codefile_normal_begin = codefile_normal_begin.replace("{{ filename }}", settings["filename"])
        codefile_normal_end = codecs.open("courses/codefile-normal-end.html", "r", "utf-8").read().strip()
        self.current_filename = settings["filename"]
        for part in block:
            yield codefile_normal_begin
            yield '{{ %s }}' % settings["filename"]  # TODO: Output the file here instead of in the view.
            yield codefile_normal_end
    def settings_codefile(self, matchobj):
        filename = escape(matchobj.group("filename"))
        
        settings = {"filename" : filename}
        return settings

    def block_code(self, block, settings):
        for part in block:
            yield u'<pre class="normal">'
            line = self.lines.next()
            while not line.startswith("}}}"):
                yield escape(line) + "\n"
                line = self.lines.next()
            yield u'</pre>\n'
    def settings_code(self, matchobj):
        pass

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
                yield u'<td>%s</td>' % cell
        yield u'</tr>'
        if not self.table_header_used and settings["thead"]:
            self.table_header_used = True
            yield u'</thead>'
    def settings_table(self, matchobj):
        cells = matchobj.group(0).strip().split("||")
        cells.pop() # Remove the entry after last ||
        cells.pop(0) # Remove the entry before first ||
        thcells = [cell.startswith("!") for cell in cells]
        cells = [cell.lstrip("!") for cell in cells]
        thead = False not in thcells
        
        settings = {"cells" : cells,
                    "thcells" : thcells,
                    "thead" : thead,}
        return settings

    def set_fileroot(self, fileroot):
        self.fileroot = fileroot

    def get_current_filename(self):
        return self.current_filename
    def get_current_taskname(self):
        return self.current_taskname
        
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



if __name__ == "__main__":
    test_file = open("test1.txt")
    
    test = ContentParser(test_file)
    html = u""
    for line in test.parse():
        html += line
    
    print html
