import re

from django.core import mail
from django.conf import settings
from django.template.loader import get_template


def remove_extra_line_breaks(text):
    """
    Replaces multiple line breaks with just one.

    Useful to suppress empty line breaks generated by Django's template tags
    in emails text templates.
    """
    return re.sub(r"\n{3,}", "\n\n", text)


def get_email_text_template(template, context):
    context.update(
        {
            "itou_protocol": settings.ITOU_PROTOCOL,
            "itou_fqdn": settings.ITOU_FQDN,
            "itou_email_contact": settings.ITOU_EMAIL_CONTACT,
        }
    )
    return remove_extra_line_breaks(get_template(template).render(context).strip())


def get_email_message(
    to, context, subject, body, from_email=settings.DEFAULT_FROM_EMAIL, bcc=None
):
    return mail.EmailMessage(
        from_email=from_email,
        to=to,
        bcc=bcc,
        subject=get_email_text_template(subject, context),
        body=get_email_text_template(body, context),
    )
