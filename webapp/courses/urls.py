from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views, staff_views, user_views, calendar_views, message_views

app_name = "courses"

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("login/", user_views.login, name="login"),
    path("logout/", user_views.logout, name="logout"),
    path(
        "groups/<course:course>/<instance:instance>/",
        user_views.group_info,
        name="group_info",
    ),
    path(
        "groups/<course:course>/<instance:instance>/create/",
        staff_views.create_group,
        name="create_group",
    ),
    path(
        "groups/<course:course>/<instance:instance>/manage/",
        staff_views.group_management,
        name="group_management",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<group:group>/invite/",
        user_views.invite_members,
        name="invite_members",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<group:group>/rename/",
        staff_views.rename_group,
        name="rename_group",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<group:group>/remove/",
        staff_views.remove_group,
        name="remove_group",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<group:group>/add_member/",
        staff_views.add_member,
        name="add_member",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<group:group>/set_supervisor/",
        staff_views.set_supervisor,
        name="set_supervisor",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<group:group>/<user:member>/remove/",
        staff_views.remove_member,
        name="remove_member",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<invite:invite>/accept/",
        user_views.accept_invitation,
        name="accept_invitation",
    ),
    path(
        "groups/<course:course>/<instance:instance>/<group:group>/<invite:invite>/cancel/",
        user_views.cancel_invitation,
        name="cancel_invitation",
    ),
    # For viewing and changing user information
    path(
        "answers/<user:user>/<course:course>/<instance:instance>/"
        "<content:exercise>/<answer:answer>/",
        views.get_file_exercise_evaluation,
        name="get_file_exercise_evaluation",
    ),
    path(
        "answers/<user:user>/<course:course>/<instance:instance>/<content:exercise>/",
        views.show_answers,
        name="show_answers",
    ),
    path(
        "answers/<user:user>/<course:course>/<instance:instance>/"
        "<answer:answer>/<str:filename>/show/",
        views.show_answer_file_content,
        name="show_answer_file",
    ),
    path("user/<user:user>/", user_views.user),
    path("profile/", user_views.user_profile),
    path("profile/save/", user_views.user_profile_save),
    # For calendar POST requests
    path(
        "calendar/<calendar:calendar>/<event:event>/",
        calendar_views.calendar_reservation,
        name="calendar_reservation",
    ),
    path(
        "calendar/<course:course>/<instance:instance>/<calendar:calendar>/config/",
        calendar_views.calendar_config,
        name="calendar_config",
    ),
    path(
        "calendar/<course:course>/<instance:instance>/<calendar:calendar>/schedule/",
        calendar_views.calendar_scheduling,
        name="calendar_scheduling",
    ),
    path(
        "calendar/<course:course>/<instance:instance>/<calendar:calendar>/message/",
        calendar_views.message_reservers,
        name="message_reservers",
    ),
    path(
        "calendar/<course:course>/<instance:instance>/<event:event>/slots/<str:action>/",
        calendar_views.adjust_slots,
        name="adjust_calendar_slots",
    ),
    path(
        "preview/<str:field_name>",
        staff_views.content_preview,
        name="content_preview",
    ),
    # Staff URLs for editing content
    path(
        "staff/<course:course>/<instance:instance>/instance_settings/",
        staff_views.instance_settings,
        name="instance_settings",
    ),
    path(
        "staff/<course:course>/<instance:instance>/freeze_instance/",
        staff_views.freeze_instance,
        name="freeze_instance",
    ),
    path(
        "staff/<course:course>/<instance:instance>/clone_instance/",
        staff_views.clone_instance,
        name="clone_instance",
    ),
    path(
        "staff/<course:course>/<instance:instance>/edit_grading/",
        staff_views.edit_grading,
        name="edit_grading",
    ),
    path(
        "staff/<course:course>/<instance:instance>/create_content_node/",
        staff_views.create_content_node,
        name="create_content_node",
    ),
    path(
        "staff/<course:course>/<instance:instance>/remove_content_node/<int:node_id>/",
        staff_views.remove_content_node,
        name="remove_content_node",
    ),
    path(
        "staff/<course:course>/<instance:instance>/node_settings/<int:node_id>/",
        staff_views.node_settings,
        name="node_settings",
    ),
    path(
        "staff/<course:course>/<instance:instance>/move_content_node/"
        "<int:target_id>/<str:placement>/",
        staff_views.move_content_node,
        name="move_content_node",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<user:user>/",
        message_views.direct_message,
        name="send_message",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/regen_cache/",
        staff_views.regen_page_cache,
        name="regen_page_cache",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/editform/<str:action>/",
        staff_views.edit_form,
        name="content_edit_form",
    ),
    path(
        "staff/<course:course>/<instance:instance>/<content:content>/add/",
        staff_views.add_form,
        name="content_add_form",
    ),
    path(
        "staff/<course:course>/<instance:instance>/regen_cache/",
        staff_views.regen_instance_cache,
        name="regen_instance_cache",
    ),
    path(
        "staff/<course:course>/<instance:instance>/termify/",
        staff_views.termify,
        name="termify",
    ),
    path(
        "staff/<course:course>/<instance:instance>/export/",
        staff_views.export_instance,
        name="export",
    ),
    path(
        "staff/<course:course>/<instance:instance>/import/",
        staff_views.import_instance,
        name="import",
    ),

    # Staff URLs for messages
    path(
        "staff/<course:course>/<instance:instance>/mass_email/",
        message_views.mass_email,
        name="mass_email",
    ),
    path(
        "staff/<course:course>/<instance:instance>/load_message/<int:msgid>/",
        message_views.load_message,
        name="load_message",
    ),
    # Help pages
    path(
        "help/",
        views.help_list,
        name="help_list",
    ),
    path(
        "help/markup/",
        views.markup_help,
        name="markup_help",
    ),
    path(
        "terms/",
        views.terms,
        name="terms",
    ),
    # Enrollment views
    path("enroll/<course:course>/<instance:instance>/", views.enroll, name="enroll"),
    path("withdraw/<course:course>/<instance:instance>/", views.withdraw, name="withdraw"),
    # Course front page and content views
    path(
        "answers/<user:user>/<course:course>/<instance:instance>/"
        "<answer:answer>/<str:filename>/download/",
        views.download_answer_file,
        name="download_answer_file",
    ),
    path("<course:course>/", views.course_instances, name="course_instances"),
    path("<course:course>/<instance:instance>/", views.course, name="course"),
    path(
        "<course:course>/<instance:instance>/<content:content>/",
        views.content,
        name="content",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/<int:pagenum>/",
        views.content,
        name="content_part",
    ),
    # Download views
    path(
        "file-download/embedded/<course:course>/<instance:instance>/<file:mediafile>/",
        views.download_embedded_file,
        name="download_embedded_file",
    ),
    path(
        "file-download/media/<slug:file_slug>/<str:field_name>/<str:filename>/",
        views.download_media_file,
        name="download_media_file",
    ),
    path(
        "file-download/template-backend/<int:exercise_id>/<str:field_name>/<str:filename>/",
        views.download_template_exercise_backend,
        name="download_template_exercise_backend",
    ),
    # Exercise sending for checking, progress and evaluation views
    path(
        "<course:course>/<instance:instance>/<content:content>/<revision:revision>/check/",
        views.check_answer,
        name="check",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/"
        "<revision:revision>/exercise-session/",
        views.get_repeated_template_session,
        name="get_repeated_template_session",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/"
        "<revision:revision>/progress/<slug:task_id>/",
        views.check_progress,
        name="check_progress",
    ),
    path(
        "<course:course>/<instance:instance>/<content:content>/"
        "<revision:revision>/evaluation/<slug:task_id>/",
        views.file_exercise_evaluation,
        name="file_exercise_evaluation",
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
