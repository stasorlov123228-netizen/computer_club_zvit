from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Computer, Tariff


class DemoDataCommandTests(TestCase):
    def test_seed_command_is_idempotent_and_only_adds_missing_catalog_rows(self):
        output = StringIO()
        call_command('seed_demo_data', stdout=output)
        first_counts = (Computer.objects.count(), Tariff.objects.count())
        call_command('seed_demo_data', stdout=output)
        self.assertEqual(
            (Computer.objects.count(), Tariff.objects.count()), first_counts,
        )
        self.assertEqual(first_counts, (4, 4))
