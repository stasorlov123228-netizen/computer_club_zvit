from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from .forms import BookingModelForm
from .models import Booking, Computer, Tariff
from .views import (
    BookingCreateView, BookingDeleteView, BookingDetailView,
    BookingListView, BookingUpdateView,
)


class BookingRoutingAndViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('owner', password='StrongPassw0rd!')
        cls.other = User.objects.create_user('other', password='StrongPassw0rd!')
        cls.staff = User.objects.create_user(
            'staff', password='StrongPassw0rd!', is_staff=True,
        )
        cls.computer = Computer.objects.create(name='PC default')
        cls.tariff = Tariff.objects.create(name='Standard', price_per_hour=Decimal('100.00'))
        start = timezone.now() + timedelta(days=2)
        cls.booking = Booking.objects.create(
            user=cls.owner, customer_name='Owner', phone='+380671234567',
            computer=cls.computer, tariff=cls.tariff,
            start_time=start, end_time=start + timedelta(hours=2),
        )

    def test_legacy_and_crud_routes_reverse_to_expected_views(self):
        self.assertEqual(reverse('home'), '/')
        checks = (
            ('booking_list', [], BookingListView),
            ('booking_create', [], BookingCreateView),
            ('booking_detail', [self.booking.pk], BookingDetailView),
            ('booking_update', [self.booking.pk], BookingUpdateView),
            ('booking_delete', [self.booking.pk], BookingDeleteView),
        )
        for name, args, view_class in checks:
            with self.subTest(name=name):
                match = resolve(reverse(name, args=args))
                self.assertIs(match.func.view_class, view_class)

    def test_model_absolute_urls_resolve_to_registered_detail_routes(self):
        self.assertEqual(
            self.booking.get_absolute_url(),
            reverse('booking_detail', args=[self.booking.pk]),
        )
        self.assertEqual(
            self.computer.get_absolute_url(),
            reverse('computer_detail', args=[self.computer.pk]),
        )
        self.assertEqual(
            self.tariff.get_absolute_url(),
            reverse('tariff_detail', args=[self.tariff.pk]),
        )

    def test_booking_list_is_scoped_and_really_paginates_at_five(self):
        for index in range(6):
            computer = Computer.objects.create(name=f'Extra PC {index}')
            Booking.objects.create(
                user=self.owner, customer_name=f'Owner {index}',
                phone='+380671234567', computer=computer, tariff=self.tariff,
                start_time=self.booking.start_time,
                end_time=self.booking.end_time,
            )
        Booking.objects.create(
            user=self.other, customer_name='Other owner', phone='+380671234567',
            computer=Computer.objects.create(name='Other PC'), tariff=self.tariff,
            start_time=self.booking.start_time, end_time=self.booking.end_time,
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse('booking_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paginator'].count, 7)
        self.assertEqual(response.context['paginator'].per_page, 5)
        self.assertEqual(len(response.context['bookings']), 5)
        self.assertEqual(response.context['paginator'].num_pages, 2)
        self.assertNotContains(response, 'Other owner')

    def test_other_user_cannot_access_booking_detail_edit_or_delete(self):
        self.client.force_login(self.other)
        for name in ('booking_detail', 'booking_update', 'booking_delete'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=[self.booking.pk]))
                self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.client.post(
                reverse('booking_update', args=[self.booking.pk]),
                {'customer_name': 'Hijacked'},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse('booking_delete', args=[self.booking.pk]), {},
            ).status_code,
            404,
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.customer_name, 'Owner')

    def test_create_update_and_delete_use_the_expected_http_methods(self):
        self.client.force_login(self.owner)
        start = timezone.localtime(timezone.now() + timedelta(days=3))
        payload = {
            'customer_name': 'Created through POST',
            'phone': '0671234567',
            'computer': self.computer.pk,
            'tariff': self.tariff.pk,
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': (start + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            'user': self.other.pk,
        }
        create_response = self.client.post(reverse('booking_create'), payload)
        self.assertEqual(create_response.status_code, 302)
        created = Booking.objects.get(customer_name='Created through POST')
        self.assertEqual(created.user, self.owner)

        update_response = self.client.post(
            reverse('booking_update', args=[created.pk]),
            {**payload, 'customer_name': 'Updated through POST'},
        )
        self.assertEqual(update_response.status_code, 302)
        created.refresh_from_db()
        self.assertEqual(created.customer_name, 'Updated through POST')
        self.assertEqual(created.user, self.owner)

        confirm_response = self.client.get(reverse('booking_delete', args=[created.pk]))
        self.assertEqual(confirm_response.status_code, 200)
        self.assertTrue(Booking.objects.filter(pk=created.pk).exists())
        delete_response = self.client.post(reverse('booking_delete', args=[created.pk]))
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Booking.objects.filter(pk=created.pk).exists())

    def test_staff_can_view_all_bookings_and_anonymous_user_is_redirected(self):
        Booking.objects.create(
            user=self.other, customer_name='Other owner', phone='+380671234567',
            computer=Computer.objects.create(name='Other PC'), tariff=self.tariff,
            start_time=self.booking.start_time, end_time=self.booking.end_time,
        )
        response = self.client.get(reverse('booking_list'))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(reverse('booking_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paginator'].count, 2)


class BookingModelFormTests(TestCase):
    def setUp(self):
        self.computer = Computer.objects.create(name='PC default')
        self.tariff = Tariff.objects.create(name='Standard', price_per_hour=Decimal('100.00'))
        self.start = timezone.now() + timedelta(days=2)

    def form_data(self, **overrides):
        data = {
            'customer_name': 'Test Client',
            'phone': '+380671234567',
            'computer': self.computer.pk,
            'tariff': self.tariff.pk,
            'start_time': timezone.localtime(self.start).strftime('%Y-%m-%dT%H:%M'),
            'end_time': timezone.localtime(self.start + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
        }
        data.update(overrides)
        return data

    def test_valid_ukrainian_phone_and_domestic_format(self):
        for number, expected in (
            ('+380671234567', '+380671234567'),
            ('0671234567', '+380671234567'),
        ):
            form = BookingModelForm(self.form_data(phone=number))
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data['phone'], expected)

    def test_invalid_phone_and_non_positive_interval_are_rejected(self):
        form = BookingModelForm(self.form_data(phone='+48123456789'))
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        form = BookingModelForm(self.form_data(
            end_time=timezone.localtime(self.start).strftime('%Y-%m-%dT%H:%M'),
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)

    def test_overlapping_booking_is_rejected(self):
        Booking.objects.create(
            customer_name='Existing', phone='+380671234567',
            computer=self.computer, tariff=self.tariff,
            start_time=self.start, end_time=self.start + timedelta(hours=2),
        )
        form = BookingModelForm(self.form_data(
            start_time=timezone.localtime(self.start + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'),
            end_time=timezone.localtime(self.start + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M'),
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('computer', form.errors)
