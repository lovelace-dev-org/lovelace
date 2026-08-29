from django.contrib import admin

from reversion.admin import VersionAdmin

from task_ws.models import XtermWidgetSettings, TurtleWidgetSettings
# Register your models here.

class XtermWidgetAdmin(VersionAdmin):

    content_type = "XTERM"
    save_on_top = True
    list_display = ["slug", "course"]


class TurtleWidgetAdmin(VersionAdmin):

    content_type = "TURTLE"
    save_on_top = True
    list_display = ["slug", "course"]

admin.site.register(XtermWidgetSettings, XtermWidgetAdmin)
admin.site.register(TurtleWidgetSettings, TurtleWidgetAdmin)
