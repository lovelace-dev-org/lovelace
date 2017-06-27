from django import forms
import django.conf

def validate_username_not_email(value):
    if "@" in value:
        raise forms.ValidationError(
            "Email addresses are not valid usernames",
        )

username_validators = [validate_username_not_email]


if 'shibboleth' in django.conf.settings.INSTALLED_APPS:
    
    from shibboleth.middleware import ShibbolethRemoteUserMiddleware
    from courses.models import UserProfile
    
    class LovelaceShibbolethRemoteUser(ShibbolethRemoteUserMiddleware):
    
        def make_profile(self, user, shib_meta):
            profile = UserProfile()
            profile.user = user
            profile.student_id = shib_meta["student_id"]
            profile.save()
            
