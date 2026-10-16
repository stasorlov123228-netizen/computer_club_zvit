from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations
from django.utils import timezone


def create_booking_payments(apps, schema_editor):
    Booking = apps.get_model('club', 'Booking')
    Payment = apps.get_model('club', 'Payment')
    database = schema_editor.connection.alias

    for booking in Booking.objects.using(database).select_related(
        'tariff',
    ).iterator():
        if Payment.objects.using(database).filter(
            booking_id=booking.pk,
        ).exists():
            continue

        duration_hours = Decimal(
            str((booking.end_time - booking.start_time).total_seconds())
        ) / Decimal('3600')
        amount = (
            booking.tariff.price_per_hour * duration_hours
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        is_paid = booking.payment_status == 'paid'
        Payment.objects.using(database).create(
            booking_id=booking.pk,
            amount=amount,
            is_paid=is_paid,
            status='paid' if is_paid else 'unpaid',
            paid_at=timezone.now() if is_paid else None,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0006_userprofile'),
    ]

    operations = [
        migrations.RunPython(
            create_booking_payments,
            migrations.RunPython.noop,
        ),
    ]
