from django.conf import settings
from django.core.mail import get_connection, EmailMessage
from django.utils import translation

def send_error_report(instance, content, revision, errors, answer_url):
    recipient = instance.email
    mailfrom = "{}-notices@{}".format(instance.slug, settings.ALLOWED_HOSTS[0])
    title = "[LOVELACE NOTIFY] Checker error in {}".format(content.name)
    body = ""
    body += "An error occurred during checking of student submission.\n"
    body += "Context Information:\n"
    body += "Content name: {}\n".format(content.name)
    body += "Course instance: {}\n".format(instance.name)
    body += "Revision: {}\n".format(revision)
    body += "\n"
    body += "Link to answer:\n"
    body += "{}\n".format(answer_url)
    body += "\n"
    
    for i, error in enumerate(errors, start=1):
        body += "Error #{} Details\n".format(i)
        body += "=============\n"
        body += error
        body += "\n\n"
    
    connection = get_connection()
    mail = EmailMessage(
        title, body, mailfrom, [recipient],
        connection=connection
    )
    mail.send()
    
def send_welcome_email(instance, user=None, lang_code=None, userlist=None):
    if not instance.welcome_message:
        return
    
    if lang_code is None:
        lang_code = translation.get_language()

    with translation.override(lang_code):
        if user is not None:
            recipients = [user.email]
        else:
            recipients = userlist.values_list("email", flat=True)
            print(recipients)
            
        mailfrom = "{}-notices@{}".format(instance.slug, settings.ALLOWED_HOSTS[0])
        title = "[{}]".format(instance.course.name)
        body = instance.welcome_message
        reply_to = instance.email
        
        connection = get_connection()
        mail = EmailMessage(
            title, body, mailfrom, recipients,
            headers={"Reply-to": reply_to},
            connection=connection
        )
        mail.send()
    
