from django import forms
from allauth.account.adapter import DefaultAccountAdapter

try:
    from shibboleth.app_settings import LOGOUT_SESSION_KEY
except:
    shib_installed = False
    LOGOUT_SESSION_KEY = ""
else:    
    shib_installed = True

def validate_username_not_email(value):
    if "@" in value:
        raise forms.ValidationError(
            "Email addresses are not valid usernames",
        )

username_validators = [validate_username_not_email]

class LovelaceAccountAdapter(DefaultAccountAdapter):
    
    def logout(self, request):
        """
        If Shibboleth is in use, restores the session token that prevents 
        django-shibboleth from automatically reauthenticating after django auth
        logout has flushed the session. This prevents a bug where a previous 
        Shibboleth authentication is restored if allauth login is used in the 
        same browser session and then logged out. 
        """
        
        if shib_installed:
            shib_logout_key = request.session.get(LOGOUT_SESSION_KEY, False)
            
        super().logout(request)
        
        if shib_installed:
            request.session[LOGOUT_SESSION_KEY] = True
            
    
        