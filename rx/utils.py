from django.core.mail import send_mail
from django.conf import settings

def send_stock_alert_email(medicine_name, current_stock, reorder_level):
    subject = f"CRITICAL STOCK ALERT: {medicine_name}"
    message = f"Medicine: {medicine_name}\nCurrent Stock: {current_stock}\nReorder Level: {reorder_level}\n\nPlease restock immediately."
    # Admin email should be defined in settings or handled dynamically
    admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
