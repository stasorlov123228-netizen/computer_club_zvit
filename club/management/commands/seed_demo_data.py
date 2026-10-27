from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from club.models import Booking, Computer, Tariff


class Command(BaseCommand):
    help = 'Creates demo data and one guest booking.'

    def handle(self, *args, **options):
        tariffs = {
            'STANDART': Decimal('100.00'),
            'PRO': Decimal('150.00'),
            'VIP': Decimal('200.00'),
            'STREAM': Decimal('250.00'),
        }
        computers = (
            'DEMO defolt',
            'DEMO pro',
            'DEMO vip',
            'DEMO stream',
        )
        created_tariffs = 0
        created_computers = 0
        created_bookings = 0

        for name, price in tariffs.items():
            tariff = Tariff.objects.filter(name__iexact=name).first()
            created = tariff is None
            if created:
                Tariff.objects.create(name=name, price_per_hour=price)
            created_tariffs += int(created)

        for name in computers:
            _, created = Computer.objects.get_or_create(name=name)
            created_computers += int(created)

        # One idempotent guest booking demonstrates the booking and payment
        # records without creating an account with a known demo password.
        if not Booking.objects.filter(customer_name='Demo Customer').exists():
            computer = Computer.objects.filter(
                name__startswith='DEMO ', manual_occupied=False,
            ).exclude(status='maintenance').order_by('name').first()
            tariff = Tariff.objects.order_by('price_per_hour', 'name').first()
            if computer and tariff:
                start = timezone.localtime().replace(
                    hour=12, minute=0, second=0, microsecond=0,
                ) + timedelta(days=1)
                for _ in range(14 * 24):
                    end = start + timedelta(hours=1)
                    conflict = Booking.objects.filter(
                        computer=computer, start_time__lt=end, end_time__gt=start,
                    ).exclude(status='cancelled').exists()
                    if not conflict:
                        Booking.objects.create(
                            customer_name='Demo Customer',
                            phone='+380000000000',
                            computer=computer, tariff=tariff,
                            start_time=start, end_time=end,
                            payment_method='cash', payment_status='unpaid',
                            status='pending',
                        )
                        created_bookings = 1
                        break
                    start += timedelta(hours=1)

        self.stdout.write(self.style.SUCCESS(
            'Demo data ready: added {} tariffs, {} computers, {} bookings. '
            'Existing records were not changed.'.format(
                created_tariffs, created_computers, created_bookings,
            )
        ))
