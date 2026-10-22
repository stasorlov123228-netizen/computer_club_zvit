from decimal import Decimal

from django.core.management.base import BaseCommand

from club.models import Computer, Tariff


class Command(BaseCommand):
    help = 'Створює демонстраційні тарифи та комп’ютери, яких ще немає.'

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

        for name, price in tariffs.items():
            tariff = Tariff.objects.filter(name__iexact=name).first()
            created = tariff is None
            if created:
                Tariff.objects.create(name=name, price_per_hour=price)
            created_tariffs += int(created)

        for name in computers:
            _, created = Computer.objects.get_or_create(name=name)
            created_computers += int(created)

        self.stdout.write(self.style.SUCCESS(
            'Демо-дані готові: додано тарифів {}, комп’ютерів {}. '
            'Наявні записи не змінювалися.'.format(
                created_tariffs, created_computers,
            )
        ))
