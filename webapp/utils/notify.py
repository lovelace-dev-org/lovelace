from django.core.mail import get_connection, EmailMessage


def send_error_report(instance, content, revision, errors, answer_url):
    recipient = instance.email
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
    
    mail = EmailMessage(title, body, mailfrom, [recipient], headers={"Reply-to": reply_to}, connection=connection)
    print(body)
    #mail.send()