from django.conf import settings
from django.core.mail import get_connection, EmailMessage, send_mass_mail
from django.utils import translation
from utils.formatters import display_name

def send_error_report(instance, content, revision, errors, answer_url):
    """
    Sends an error report to course staff about a checking program crashing.
    The report is sent to the email address listed in the course instance
    attributes. The email shows context information about the checking
    * content name
    * course instance 
    * revision used
    
    A link to the student's answers where the answer that triggered the error
    is highlighted is also provided.
    """

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
    """
    Sends a welcome email if one is specified for the course instance. Can be
    sent to either one user, or a list of users. If language code is not
    provided, the current language will be used for selecting the translated
    field.
    """
    
    if not instance.welcome_message:
        return
    
    if lang_code is None:
        lang_code = translation.get_language()

    with translation.override(lang_code):
        if user is not None:
            recipients = [user.email]
        else:
            recipients = userlist.values_list("email", flat=True)
            
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
    
def send_email(recipients, sender, title, body):
    """
    Generic email sending utility function. 
    """

    connection = get_connection()
    sender = '"{name}" <{email}>'.format(name=display_name(sender), email=sender.email),
    messages = []
    for recipient in recipients:
        messages.append((
            title,
            body,
            sender,
            [recipient],
        ))
    send_mass_mail(
        messages,
        connection=connection
    )
    