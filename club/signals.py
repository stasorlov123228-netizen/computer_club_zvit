from decimal import Decimal, ROUND_HALF_UP

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Booking, Payment


@receiver(post_save, sender=Booking)
def sync_booking_payment(sender, instance, **kwargs):
    duration_hours = Decimal(
        str((instance.end_time - instance.start_time).total_seconds())
    ) / Decimal('3600')
    amount = (
        instance.tariff.price_per_hour * duration_hours
    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
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
