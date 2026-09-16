from celery import shared_task
from django.core.mail import send_mail
from django.template import Template, Context
from django.conf import settings

import logging

logger = logging.getLogger(__name__)

@shared_task
def send_async_email(subject, body, to_email):
    """
    Generic task to send an email asynchronously.
    """
    logger.info(f"Sending async email to {to_email} with subject: {subject}")
    
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info(f"Successfully sent email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


@shared_task
def process_due_soon_notifications():
    """
    Cron job task to check for books due in 2 days and send notifications.
    """
    logger.info("Processing due soon notifications...")
    from transactions.models import Transaction
    from .models import NotificationPreference, Notification, EmailTemplate
    from datetime import date, timedelta
    
    target_date = date.today() + timedelta(days=2)
    due_soon_txns = Transaction.objects.filter(
        due_date=target_date, 
        status="ISSUED"
    ).select_related('member', 'book', 'organization')
    
    count = 0
    for txn in due_soon_txns:
        # Check preferences
        pref, _ = NotificationPreference.objects.get_or_create(user=txn.member)
        
        # 1. In-App Notification
        if pref.in_app_due_soon:
            Notification.objects.create(
                organization=txn.organization,
                user=txn.member,
                title="Book Due Soon",
                message=f"Your borrowed book '{txn.book.title}' is due on {txn.due_date}.",
                notification_type="INFO"
            )
            
        # 2. Email Notification
        if pref.email_due_soon and txn.member.email:
            template = EmailTemplate.objects.filter(
                organization=txn.organization, 
                event_type="DUE_SOON", 
                is_active=True
            ).first()
            
            if template:
                # Compile template
                t_sub = Template(template.subject)
                t_body = Template(template.body_text)
                ctx = Context({"user": txn.member, "book": txn.book, "transaction": txn})
                
                subject = t_sub.render(ctx)
                body = t_body.render(ctx)
            else:
                # Default fallback
                subject = f"Library Notice: {txn.book.title} is due soon"
                body = f"Hello {txn.member.first_name},\n\nThis is a friendly reminder that '{txn.book.title}' is due back at the library on {txn.due_date}.\n\nThank you!"
                
            send_async_email.delay(subject, body, txn.member.email)
            count += 1
            
    return f"Sent {count} due soon notifications"
