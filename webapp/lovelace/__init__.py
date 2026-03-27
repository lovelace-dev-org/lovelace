from __future__ import absolute_import
from collections import defaultdict
from django.conf import settings


# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
if settings.ENABLE_CELERY:
    from .celery import app as celery_app
    __all__ = ["celery_app"]

plugins = {                         # Overrideable methods + Required functions
    "answer-actions": set(),        # get_answer_actions_extra, includes.get_answer_actions
    "base-static": set(),           # includes.get_basic_static_includes
    "clone": set(),                 # models.clone_models
    "content-addon": set(),         # get_content_additions, includes.get_content_page_additions
    "content-menu": set(),          # includes.get_content_menu_options
    "context_links": set(),         # models.update_context_links
    "embed-extra": set(),           # get_student_extra, get_staff_extra,
                                    # includes.get_embed_frame_extra
    "embed-menu": set(),            # includes.get_embed_frame_options
    "exercise-triggers": set(),     # includes.get_exercise_trigger_callbacks
    "export": set(),                # models.export_models
    "freeze": set(),                # models.freeze_context_links
    "import": set(),                # models.import_models
    "routing": set(),               # routing.websocket_url_patterns
    "task_reference": set(),        # models.delete_orphan_references
    "urls": set(),                  # urls
    "user-menu": set(),             # includes.get_user_menu_options
}

def register_plugin(module, tags):
    for tag in tags:
        plugins[tag].add(module)

