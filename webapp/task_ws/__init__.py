import sys
from lovelace import register_plugin

register_plugin(sys.modules[__name__], ["export", "import"])
