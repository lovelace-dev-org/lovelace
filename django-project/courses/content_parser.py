# -*- coding: utf-8 -*-
# http://wiki.sheep.art.pl/Wiki%20Markup%20Parser%20in%20Python

import re
import itertools

class ContentParser(object):
    block = {
        "bullet" : ur"^\s*[*]\s+",
        "codefile" : ur"[{]{3}\!(?P<filename>[^\s]+)\s*[}]{3}$",
        "code" : ur"^[{]{3}\s*$",
        "empty" : ur"^\s*$",
        "heading" : ur"^\s*(?P<len>[=]{1,6})[=]*\s*.+\s*(?P=len)\s*$",
        "indent" : ur"^[ \t]+",
    }
    block_re = re.compile(ur"|".join("(?P<%s>%s)" % kv
                          for kv in sorted(block.iteritems())))

    def __init__(self, lines=None):
        """asdf
        
        asdf
        """
        
        self.lines = lines
    
    def get_line_kind(self, line):
        matchobj = self.block_re.match(line)
        return getattr(matchobj, "lastgroup", u"paragraph"), matchobj
    
    def block_heading(self, block, settings):
        yield u"<h%d>" % settings["heading_size"]
        for line in block:
            yield line.strip("= \r\n\t")
        yield u'</h%d>\n' % settings["heading_size"]
    def settings_heading(self, matchobj):
        heading_size = len(matchobj.group("len"))
        
        settings = {"heading_size" : heading_size}
        return settings
    
    def block_paragraph(self, block, settings):
        yield u'<p>'
        for line in block:
            yield line
        yield u'</p>\n'
    def settings_paragraph(self, matchobj):
        pass
    
    def block_empty(self, block, settings):
        yield u''
    def settings_empty(self, matchobj):
        pass
    
    def block_bullet(self, block, settings):
        yield u'<ul>'
        for line in block:
            yield '<li>%s</li>' % (line.strip("* \r\n\t"))
        yield u'</ul>'
    def settings_bullet(self, matchobj):
        pass

    def block_codefile(self, block, settings):
        import codecs
        codefile_normal_begin = codecs.open("courses/codefile-normal-begin.html", "r", "utf-8").read().replace("{{ filename }}", settings["filename"]).strip()
        codefile_normal_end = codecs.open("courses/codefile-normal-end.html", "r", "utf-8").read()
        self.current_filename = settings["filename"]
        for part in block:
            yield codefile_normal_begin
            yield '{{ %s }}' % settings["filename"]
            yield codefile_normal_end
    def settings_codefile(self, matchobj):
        filename = matchobj.group("filename")
        
        settings = {"filename" : filename}
        return settings

    def block_code(self, block, settings):
        for part in block:
            yield u'<pre>'
            line = self.lines.next()
            while not line.startswith("}}}"):
                yield line + "\n"
                line = self.lines.next()
            yield u'</pre>\n'
    def settings_code(self, matchobj):
        pass

    def set_fileroot(self, fileroot):
        self.fileroot = fileroot

    def get_current_filename(self):
        return self.current_filename
        
    def parse(self):
        for group_info, block in itertools.groupby(self.lines, self.get_line_kind):
            func = getattr(self, "block_%s" % group_info[0])
            settings = getattr(self, "settings_%s" % group_info[0])(group_info[1])
            #print group_info[0], settings
            for part in func(block, settings):
                yield part




if __name__ == "__main__":
    test_file = open("test1.txt")
    
    test = ContentParser(test_file)
    html = u""
    for line in test.parse():
        html += line
    
    print html
