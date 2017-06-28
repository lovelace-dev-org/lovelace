from django import forms
import django.conf

if 'shibboleth' in django.conf.settings.INSTALLED_APPS:
    
    from shibboleth.middleware import ShibbolethRemoteUserMiddleware
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
            
