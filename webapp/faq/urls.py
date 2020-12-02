from django.urls import path

from . import views
app_name = "faq"

urlpatterns = [
    path("<course:course>/<instance:instance>/<content:exercise>/", views.get_faq_panel, name="faq_panel"),
    path("<course:course>/<instance:instance>/<content:exercise>/save/", views.save_question, name="save_form"),
    path("<course:course>/<instance:instance>/<content:exercise>/link/", views.link_question, name="link_question"),
    path("<course:course>/<instance:instance>/<content:exercise>/<str:hook>/", views.get_editable_question, name="get_editable"),
    path("<course:course>/<instance:instance>/<content:exercise>/<str:hook>/unlink/", views.unlink_question, name="unlink_question"),
    
    
    
]
    