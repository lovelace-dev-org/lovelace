from django import forms
from django.http import HttpResponseBadRequest
from django.utils.translation import gettext as _
import django.conf

if 'shibboleth' in django.conf.settings.INSTALLED_APPS:
    
    from shibboleth.middleware import ShibbolethRemoteUserMiddleware, ShibbolethValidationError
    from courses.models import UserProfile
    
    class LovelaceShibbolethRemoteUser(ShibbolethRemoteUserMiddleware):
        
        def make_profile(self, user, shib_meta):
            profile = UserProfile()
            profile.user = user
            try:
                profile.student_id = int(shib_meta["student_id"].rsplit(":", 1)[-1])
            except:
                pass
            else:
                profile.save()
            

    class ShibbolethExceptionReporter(object):

        def __init__(self, get_response):
            self.get_response = get_response
            
        def __call__(self, request):
            response = self.get_response(request)
            return response
            
        def process_exception(self, request, exception):
            if isinstance(exception, ShibbolethValidationError):
                return HttpResponseBadRequest(_(
                    "Remote authentication did not provide an email address. "
                    "The most likely cause is a delay between systems. "
                    "Please wait a few hours and try again."
                ))
            return None
