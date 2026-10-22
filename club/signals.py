
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Booking, Payment
from .services import booking_pricing


@receiver(post_save, sender=Booking)
def sync_booking_payment(sender, instance, **kwargs):
    _, amount = booking_pricing(instance)
    is_paid = instance.payment_status == 'paid'
    payment = Payment.objects.filter(booking=instance).first()
    paid_at = (
        payment.paid_at if payment and payment.paid_at
        else timezone.now()
    ) if is_paid else None
    defaults = {
        'amount': amount,
        'is_paid': is_paid,
        'status': 'paid' if is_paid else 'unpaid',
        'paid_at': paid_at,
    }
    if payment:
        Payment.objects.filter(pk=payment.pk).update(**defaults)
    else:
        Payment.objects.create(booking=instance, **defaults)
