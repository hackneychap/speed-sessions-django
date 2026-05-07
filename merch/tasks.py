from django.tasks import task
from django.core.mail import send_mail
from .models import Order

@task
def send_order_status_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        status_display = order.get_status_display()
        
        subject = f"Update on your RunTRASH Gear Order #{order.id}"
        message = f"Hi {order.customer_name},\n\nYour order status has been updated to: {status_display}.\n\nThank you for being part of the community!"
        
        send_mail(
            subject,
            message,
            'noreply@speedsessions.com',
            [order.customer_email],
            fail_silently=False,
        )
    except Order.DoesNotExist:
        pass
