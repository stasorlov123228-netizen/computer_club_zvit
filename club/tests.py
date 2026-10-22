from datetime import timedelta
from decimal import Decimal

from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Booking, Computer, Tariff
from .services import find_available_computer, get_pc_kind, get_tariff_kind
from .views.bookings import booking_success_context


class BookingSuccessTests(TestCase):
    def setUp(self):
        self.computer = Computer.objects.create(name='PC test')
        self.tariff = Tariff.objects.create(
            name='Selected tariff',
            price_per_hour=Decimal('150.00'),
        )

    def make_booking(self, hours=1, status='pending', payment_status='unpaid'):
        start = timezone.now() + timedelta(days=1)
        return Booking.objects.create(
            customer_name='Test customer',
            phone='+380000000000',
            computer=self.computer,
            tariff=self.tariff,
            start_time=start,
            end_time=start + timedelta(hours=hours),
            status=status,
            payment_status=payment_status,
        )

    def test_one_hour_pending_unpaid_booking_shows_selected_tariff_pricing(self):
        booking = self.make_booking()
        context = booking_success_context(booking)
        html = render_to_string('club/booking_success.html', context)

        self.assertEqual(context['duration_hours'], '1')
        self.assertEqual(context['price_per_hour'], Decimal('150.00'))
        self.assertEqual(context['total_amount'], Decimal('150.00'))
        self.assertContainsHTML(html, 'Бронювання очікує підтвердження')
        self.assertContainsHTML(html, 'Не оплачено')
        self.assertContainsHTML(html, '150.00 грн')

    def test_multiple_hours_uses_chosen_tariff(self):
        cheaper_tariff = Tariff.objects.create(
            name='Other tariff',
            price_per_hour=Decimal('10.00'),
        )
        booking = self.make_booking(hours=3)
        booking.tariff = self.tariff
        context = booking_success_context(booking)

        self.assertEqual(context['duration_hours'], '3')
        self.assertEqual(context['total_amount'], Decimal('450.00'))
        self.assertNotEqual(context['total_amount'], cheaper_tariff.price_per_hour * 3)

    def test_confirmed_paid_and_cancelled_statuses_are_shown(self):
        confirmed = self.make_booking(status='confirmed', payment_status='paid')
        confirmed_html = render_to_string(
            'club/booking_success.html', booking_success_context(confirmed),
        )
        self.assertContainsHTML(confirmed_html, 'Бронювання підтверджено')
        self.assertContainsHTML(confirmed_html, 'Оплачено')

        cancelled = self.make_booking(status='cancelled')
        cancelled_html = render_to_string(
            'club/booking_success.html', booking_success_context(cancelled),
        )
        self.assertContainsHTML(cancelled_html, 'Бронювання скасовано')

    def assertContainsHTML(self, html, text):
        self.assertIn(text, html)


class StandartTariffTests(TestCase):
    def test_standart_tariff_maps_to_existing_defolt_computers(self):
        computer = Computer.objects.create(name='PC test defolt')
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=1)

        self.assertEqual(get_tariff_kind('STANDART'), 'standart')
        self.assertEqual(get_pc_kind(computer.name), 'standart')
        self.assertEqual(
            find_available_computer('standart', start, end),
            computer,
        )

    def test_home_uses_the_current_tariff_price_from_database(self):
        tariff = Tariff.objects.create(
            name='STANDART',
            price_per_hour=Decimal('70.00'),
        )

        response = self.client.get(reverse('club:home'))
        self.assertContains(response, '70.00 ₴')

        tariff.price_per_hour = Decimal('85.50')
        tariff.save(update_fields=['price_per_hour'])
        response = self.client.get(reverse('club:home'))
        self.assertContains(response, '85.50 ₴')
