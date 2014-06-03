# -*- coding: utf-8 -*-
"""Dictionary of different pygments lexers and their wiki equivalent names."""

from pygments.lexers import PythonLexer, PythonConsoleLexer, PythonTracebackLexer, CLexer

highlighters = {
    u"python": PythonLexer,
    u"pythonconsole": PythonConsoleLexer,
    u"pythontraceback": PythonTracebackLexer,
    u"c": CLexer,
}
