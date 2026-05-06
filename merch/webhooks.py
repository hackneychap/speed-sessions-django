from django.dispatch import receiver
from djstripe.signals import WEBHOOK_SIGNALS
from .models import Order

@receiver(WEBHOOK_SIGNALS["invoice.paid"])
def handle_invoice_paid(sender, event, **kwargs):
    """
    Update local Order status when the corresponding Stripe Invoice is paid.
    """
    # event is a djstripe.models.Event instance
    invoice_data = event.data['object']
    stripe_invoice_id = invoice_data['id']
    
    try:
        order = Order.objects.get(stripe_invoice_id=stripe_invoice_id)
        order.status = 'PAID_AWAITING_PRINT'
        order.save()
    except Order.DoesNotExist:
        # Log error or handle cases where the invoice ID doesn't match our database
        pass

@receiver(WEBHOOK_SIGNALS["invoice.payment_failed"])
def handle_invoice_payment_failed(sender, event, **kwargs):
    """
    Update local Order status when the corresponding Stripe Invoice payment fails.
    """
    invoice_data = event.data['object']
    stripe_invoice_id = invoice_data['id']
    
    try:
        order = Order.objects.get(stripe_invoice_id=stripe_invoice_id)
        order.status = 'PAYMENT_FAILED'
        order.save()
    except Order.DoesNotExist:
        pass
