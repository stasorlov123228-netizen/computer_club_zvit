<<<<<<< HEAD
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from .models import Booking, Computer, Payment, Tariff, UserProfile
from .phone_numbers import validate_phone_number
from .views import CustomUserCreationForm, PaymentCardForm


class AdminHomeLinkTests(TestCase):
    def test_admin_user_sees_admin_panel_link_in_home_header(self):
        admin = User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
            is_staff=False,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'АДМІН-ПАНЕЛЬ')
        self.assertContains(
            response,
            f'href="{reverse("admin_panel")}"',
        )

    def test_admin_user_can_open_admin_panel_based_on_admin_base(self):
        admin = User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
            is_staff=False,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('admin_panel'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'club/admin_panel.html')
        self.assertContains(response, 'admin-nav')

    def test_admin_staff_user_sees_admin_panel_link(self):
        admin = User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("admin_panel")}"',
        )
        self.assertContains(response, 'АДМІН-ПАНЕЛЬ')

    def test_non_admin_non_staff_does_not_see_admin_panel_link(self):
        user = User.objects.create_user(
            username='regular-user',
            password='StrongPassw0rd!xyz',
            is_staff=False,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'АДМІН-ПАНЕЛЬ')

    def test_staff_user_keeps_admin_access_when_returning_to_home(self):
        staff_user = User.objects.create_user(
            username='stas',
            password='StrongPassw0rd!xyz',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(staff_user)

        panel_response = self.client.get(reverse('admin_computers'))
        self.assertEqual(panel_response.status_code, 200)
        home_response = self.client.get(reverse('home'))

        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(home_response.wsgi_request.user, staff_user)
        self.assertContains(home_response, 'АДМІН-ПАНЕЛЬ')
        self.assertEqual(
            self.client.get(reverse('admin_panel')).status_code,
            200,
        )

    def test_admin_home_link_goes_to_site_and_logout_clears_session(self):
        admin = User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
            is_staff=False,
        )
        self.client.force_login(admin)

        panel_response = self.client.get(reverse('admin_computers'))

        self.assertContains(
            panel_response,
            f'href="{reverse("home")}" class="home-link">НА ГОЛОВНУ',
        )
        self.assertContains(
            panel_response,
            f'action="{reverse("logout")}" method="post"',
        )
        self.assertEqual(
            self.client.get(reverse('home')).wsgi_request.user,
            admin,
        )

        logout_response = self.client.post(reverse('logout'))

        self.assertRedirects(logout_response, reverse('home'))
        self.assertFalse(
            self.client.get(reverse('home')).wsgi_request.user.is_authenticated
        )

    def test_admin_login_redirects_to_home_with_panel_link(self):
        User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
            is_staff=True,
        )

        response = self.client.post(reverse('login'), {
            'username': 'admin',
            'password': 'StrongPassw0rd!xyz',
        })

        self.assertRedirects(response, reverse('home'))
        home_response = self.client.get(reverse('home'))
        self.assertContains(home_response, 'АДМІН-ПАНЕЛЬ')


class AdminUsersPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
            is_staff=False,
        )
        self.client.force_login(self.admin)

    def test_user_phone_is_shown_in_admin_user_list(self):
        user = User.objects.create_user(
            username='phone-user',
            password='StrongPassw0rd!xyz',
        )
        UserProfile.objects.create(user=user, phone='+380671234567')

        response = self.client.get(reverse('admin_users'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Номер телефону')
        self.assertContains(response, '+380671234567')

    def test_admin_username_is_shown_as_admin_and_can_open_panel_sections(self):
        User.objects.create_superuser(
            username='stas',
            password='StrongPassw0rd!xyz',
        )

        users_response = self.client.get(reverse('admin_users'))
        self.assertEqual(users_response.status_code, 200)
        self.assertContains(
            users_response,
            '<strong>admin</strong>',
            html=True,
        )
        self.assertContains(
            users_response,
            '<span class="badge admin">Адміністратор</span>',
            html=True,
        )
        self.assertContains(
            users_response,
            '<span class="badge admin">Суперадмін</span>',
            html=True,
        )

        for url_name in ('admin_tariffs', 'admin_computers'):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_admin_username_can_update_computer_status_without_django_admin_login(self):
        computer = Computer.objects.create(
            name='PC-01-defolt',
            status='available',
        )

        response = self.client.post(reverse('admin_computers'), {
            'computer_id': computer.pk,
            'status': 'maintenance',
        })

        self.assertRedirects(response, reverse('admin_computers'))
        computer.refresh_from_db()
        self.assertEqual(computer.status, 'maintenance')

    def test_django_admin_lists_phone_and_role_and_saves_phone(self):
        admin_user = User.objects.create_superuser(
            username='django-admin',
            password='StrongPassw0rd!xyz',
        )
        user = User.objects.create_user(
            username='registered-client',
            password='StrongPassw0rd!xyz',
        )
        profile = UserProfile.objects.create(
            user=user,
            phone='+380671234567',
        )
        self.client.force_login(admin_user)

        changelist = self.client.get(reverse('admin:auth_user_changelist'))

        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, '+380671234567')
        self.assertContains(changelist, 'Клієнт')
        self.assertContains(changelist, 'Суперадміністратор')

        response = self.client.post(
            reverse('admin:auth_user_change', args=[user.pk]),
            {
                'username': user.username,
                'first_name': '',
                'last_name': '',
                'email': '',
                'is_active': 'on',
                'is_staff': '',
                'is_superuser': '',
                'groups': [],
                'user_permissions': [],
                'date_joined_0': user.date_joined.strftime('%Y-%m-%d'),
                'date_joined_1': user.date_joined.strftime('%H:%M:%S'),
                'profile-TOTAL_FORMS': '1',
                'profile-INITIAL_FORMS': '1',
                'profile-MIN_NUM_FORMS': '0',
                'profile-MAX_NUM_FORMS': '1',
                'profile-0-id': str(profile.pk),
                'profile-0-user': str(user.pk),
                'profile-0-phone': '+380991112233',
                '_save': 'Зберегти',
            },
        )

        self.assertRedirects(response, reverse('admin:auth_user_changelist'))
        profile.refresh_from_db()
        self.assertEqual(profile.phone, '+380991112233')


class AdminPaymentTests(TestCase):
    def test_payments_admin_shows_booking_and_current_payment_status(self):
        admin_user = User.objects.create_superuser(
            username='django-admin',
            password='StrongPassw0rd!xyz',
        )
        computer = Computer.objects.create(
            name='PC-01-defolt',
            status='available',
        )
        tariff = Tariff.objects.create(
            name='DEFAULT',
            price_per_hour=50,
        )
        start = timezone.now() + timedelta(days=1)
        booking = Booking.objects.create(
            user=None,
            customer_name='Payment Client',
            phone='+380671234567',
            computer=computer,
            tariff=tariff,
            start_time=start,
            end_time=start + timedelta(hours=2),
            payment_method='card',
            payment_status='unpaid',
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:club_payment_changelist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(booking))
        self.assertContains(response, 'НЕ ОПЛАЧЕНО')
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.amount, 100)
        self.assertFalse(payment.is_paid)

        booking.payment_status = 'paid'
        booking.save(update_fields=['payment_status'])
        response = self.client.get(reverse('admin:club_payment_changelist'))

        self.assertContains(response, 'ОПЛАЧЕНО')
        payment.refresh_from_db()
        self.assertTrue(payment.is_paid)
        self.assertEqual(payment.status, 'paid')


class SectionPageHeaderTests(TestCase):
    def test_section_page_uses_home_navigation_for_visitors(self):
        response = self.client.get(reverse('news'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="main-header"')
        self.assertContains(response, 'class="main-nav" id="main-nav"')
        self.assertContains(response, 'aria-controls="main-nav"')
        self.assertContains(response, reverse('login'))
        self.assertContains(response, 'ПОВЕРНУТИСЯ НА ГОЛОВНУ')
        self.assertContains(
            response,
            f'href="{reverse("home")}" class="home-link"',
        )
        self.assertNotContains(response, reverse('admin_panel'))

    def test_section_page_shows_admin_and_account_links_for_staff(self):
        admin_user = User.objects.create_user(
            username='stas',
            password='StrongPassw0rd!xyz',
            is_staff=True,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('news'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'АДМІН-ПАНЕЛЬ')
        self.assertContains(response, reverse('admin_panel'))
        self.assertContains(response, reverse('account'))


class StickyHeaderTests(TestCase):
    def test_headers_remain_sticky_on_account_booking_and_admin_pages(self):
        user = User.objects.create_user(
            username='sticky-user',
            password='StrongPassw0rd!xyz',
        )
        self.client.force_login(user)

        for url_name in ('account', 'booking', 'my_bookings'):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'position: sticky;')
                self.assertContains(response, 'top: 0;')

        admin = User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('admin_computers'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'position: sticky;')
        self.assertContains(response, 'top: 0;')


class PartnershipCallbackTests(TestCase):
    def test_valid_phone_shows_callback_confirmation(self):
        response = self.client.post(reverse('partnership'), {
            'phone_country': '+380',
            'phone_local': '671234567',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ми вам скоро подзвонимо.')
        self.assertContains(response, 'role="status"')
        self.assertNotContains(response, 'Номер телефону повинен')

    def test_invalid_phone_shows_validation_error_and_preserves_input(self):
        response = self.client.post(reverse('partnership'), {
            'phone_country': '+380',
            'phone_local': '123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'номер має містити 9 цифр')
        self.assertContains(response, 'value="123"')
        self.assertNotContains(response, 'Ми вам скоро подзвонимо.')

    def test_phone_longer_than_country_maximum_is_rejected(self):
        response = self.client.post(reverse('partnership'), {
            'phone_country': '+380',
            'phone_local': '6712345678',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Номер не може містити більше 9 цифр після коду країни.',
        )
        self.assertContains(response, 'value="6712345678"')
        self.assertNotContains(response, 'Ми вам скоро подзвонимо.')


class AdminBookingEditingTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='StrongPassw0rd!xyz',
            is_staff=False,
        )
        self.other_user = User.objects.create_user(
            username='booking-client',
            password='StrongPassw0rd!xyz',
        )
        self.tariff = Tariff.objects.create(
            name='DEFAULT',
            price_per_hour=50,
        )
        self.pro_tariff = Tariff.objects.create(
            name='PRO',
            price_per_hour=80,
        )
        self.computer = Computer.objects.create(
            name='Computer defolt',
            status='available',
        )
        self.pro_computer = Computer.objects.create(
            name='Computer pro',
            status='available',
        )
        self.start = (
            timezone.localtime(timezone.now()) + timedelta(days=4)
        ).replace(second=0, microsecond=0)
        self.booking = Booking.objects.create(
            user=self.other_user,
            customer_name='Booking Client',
            phone='+380671234567',
            computer=self.computer,
            tariff=self.tariff,
            start_time=self.start,
            end_time=self.start + timedelta(hours=2),
            payment_method='cash',
            payment_status='unpaid',
            status='confirmed',
        )
        self.client.force_login(self.admin)

    def post_edit(self, **overrides):
        data = {
            'computer': self.pro_computer.pk,
            'tariff': self.pro_tariff.pk,
            'start_time': (
                self.start + timedelta(hours=4)
            ).strftime('%Y-%m-%dT%H:%M'),
            'end_time': (
                self.start + timedelta(hours=6)
            ).strftime('%Y-%m-%dT%H:%M'),
            'payment_method': 'card',
            'payment_status': 'paid',
            'status': 'confirmed',
        }
        data.update(overrides)
        return self.client.post(
            reverse('edit_admin_booking', args=[self.booking.pk]),
            data,
        )

    def test_admin_without_staff_can_open_and_edit_booking(self):
        page = self.client.get(reverse('admin_bookings'))

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Редагувати бронювання')

        response = self.post_edit()

        self.assertRedirects(response, reverse('admin_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.computer, self.pro_computer)
        self.assertEqual(self.booking.tariff, self.pro_tariff)
        self.assertEqual(
            self.booking.start_time,
            self.start + timedelta(hours=4),
        )
        self.assertEqual(
            self.booking.end_time,
            self.start + timedelta(hours=6),
        )
        self.assertEqual(self.booking.payment_method, 'card')
        self.assertEqual(self.booking.payment_status, 'paid')
        self.assertEqual(self.booking.status, 'confirmed')

    def test_admin_computer_list_is_numbered_and_hides_unavailable_pcs(self):
        computers = {
            number: Computer.objects.create(
                name=f'PC-{number:02}-defolt',
            )
            for number in range(1, 56)
        }
        busy_pc = computers[4]
        Booking.objects.create(
            user=None,
            customer_name='Busy Client',
            phone='+380671234568',
            computer=busy_pc,
            tariff=self.tariff,
            start_time=self.start,
            end_time=self.start + timedelta(hours=1),
            payment_method='cash',
            status='confirmed',
        )
        Computer.objects.filter(pk=computers[3].pk).update(
            status='maintenance',
        )
        Computer.objects.filter(pk=computers[5].pk).update(
            manual_occupied=True,
        )

        response = self.client.get(reverse('admin_bookings'))

        self.assertEqual(response.status_code, 200)
        form = next(
            form
            for booking, form in response.context['booking_rows']
            if booking.pk == self.booking.pk
        )
        computer_names = list(
            form.fields['computer'].queryset.values_list('name', flat=True)
        )
        self.assertEqual(
            computer_names,
            [
                computers[number].name
                for number in range(1, 56)
                if number not in (3, 4, 5)
            ] + ['Computer defolt', 'Computer pro'],
        )
        self.assertNotIn(busy_pc.name, computer_names)
        choice_names = [
            label for value, label in form.fields['computer'].choices
        ]
        self.assertEqual(choice_names, computer_names)

    def test_admin_cannot_assign_computer_with_overlapping_booking(self):
        Booking.objects.create(
            user=None,
            customer_name='Another Client',
            phone='+380671234568',
            computer=self.pro_computer,
            tariff=self.pro_tariff,
            start_time=self.start + timedelta(hours=3),
            end_time=self.start + timedelta(hours=7),
            payment_method='cash',
            status='confirmed',
        )

        response = self.post_edit(
            start_time=(
                self.start + timedelta(hours=4)
            ).strftime('%Y-%m-%dT%H:%M'),
            end_time=(
                self.start + timedelta(hours=5)
            ).strftime('%Y-%m-%dT%H:%M'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ПК уже заброньований')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.computer, self.computer)
        self.assertEqual(self.booking.tariff, self.tariff)
        self.assertEqual(self.booking.payment_method, 'cash')
        self.assertEqual(self.booking.payment_status, 'unpaid')

    def test_admin_cannot_assign_tariff_that_does_not_match_computer(self):
        response = self.post_edit(computer=self.computer.pk)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'не відповідає вибраному тарифу')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.computer, self.computer)
        self.assertEqual(self.booking.tariff, self.tariff)

    def test_non_admin_cannot_edit_booking_from_admin_panel(self):
        self.client.force_login(self.other_user)

        response = self.post_edit()

        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.computer, self.computer)


class PhoneNumberTests(TestCase):
    def test_phone_number_is_normalized_and_country_checked(self):
        self.assertEqual(
            validate_phone_number('+380', '671234567'),
            '+380671234567',
        )

        with self.assertRaises(ValidationError):
            validate_phone_number('+380', '123')

        with self.assertRaises(ValidationError):
            validate_phone_number('+999', '123456789')

        with self.assertRaises(ValidationError):
            validate_phone_number('+380', '１２３４５６７８９')


class RegistrationPhoneTests(TestCase):
    def test_registration_renders_country_code_options(self):
        response = self.client.get(reverse('register'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Україна (+380)')
        self.assertContains(response, 'Польща (+48)')

    def test_registration_requires_and_saves_phone(self):
        form = CustomUserCreationForm(data={
            'username': 'phone-user',
            'password': 'StrongPassw0rd!xyz',
            'phone_country': '+380',
            'phone_local': '671234567',
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(
            UserProfile.objects.get(user=user).phone,
            '+380671234567',
        )

    def test_registration_rejects_invalid_phone(self):
        form = CustomUserCreationForm(data={
            'username': 'invalid-phone-user',
            'password': 'StrongPassw0rd!xyz',
            'phone_country': '+380',
            'phone_local': '123',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone_local', form.errors)


class BookingPhoneTests(TestCase):
    def test_guest_booking_requires_phone(self):
        response = self.client.post(reverse('booking'), {
            'name': 'Guest',
            'phone_country': '+380',
            'phone_local': '123',
            'tariff': 'default',
            'duration': '1',
            'date': '2027-01-01',
            'time': '12:00',
            'payment_method': 'cash',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'номер має містити')

    def test_signed_in_booking_page_does_not_ask_for_phone(self):
        user = User.objects.create_user(
            username='existing-user',
            password='StrongPassw0rd!xyz',
        )
        UserProfile.objects.create(user=user, phone='+380671234567')
        self.client.force_login(user)

        response = self.client.get(reverse('booking'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'style="display:none"')

    def test_signed_in_booking_uses_profile_phone_without_posting_it(self):
        user = User.objects.create_user(
            username='booking-user',
            password='StrongPassw0rd!xyz',
        )
        UserProfile.objects.create(user=user, phone='+380671234567')
        Tariff.objects.create(name='DEFAULT', price_per_hour=50)
        Computer.objects.create(
            name='Computer defolt',
            status='available',
        )
        self.client.force_login(user)
        start = timezone.localtime(timezone.now()) + timedelta(days=2)

        response = self.client.post(reverse('booking'), {
            'name': 'Booking User',
            'tariff': 'default',
            'duration': '1',
            'date': start.strftime('%Y-%m-%d'),
            'time': start.strftime('%H:%M'),
            'payment_method': 'cash',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['booking'].phone, '+380671234567')
        self.assertEqual(response.context['booking'].user, user)

    def test_signed_in_user_can_update_phone_in_account(self):
        user = User.objects.create_user(
            username='legacy-user',
            password='StrongPassw0rd!xyz',
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('account')).status_code, 200)

        response = self.client.post(reverse('account'), {
            'phone_country': '+48',
            'phone_local': '123456789',
            'update_phone': '',
        })

        self.assertRedirects(response, reverse('account'))
        self.assertEqual(
            UserProfile.objects.get(user=user).phone,
            '+48123456789',
        )


class BookingEditingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='booking-owner',
            password='StrongPassw0rd!xyz',
        )
        self.other_user = User.objects.create_user(
            username='other-owner',
            password='StrongPassw0rd!xyz',
        )
        self.computer = Computer.objects.create(
            name='Computer defolt',
            status='available',
        )
        self.tariff = Tariff.objects.create(
            name='DEFAULT',
            price_per_hour=50,
        )
        self.start = timezone.localtime(timezone.now()) + timedelta(days=3)
        self.booking = Booking.objects.create(
            user=self.user,
            customer_name='Booking Owner',
            phone='+380671234567',
            computer=self.computer,
            tariff=self.tariff,
            start_time=self.start,
            end_time=self.start + timedelta(hours=2),
            payment_method='cash',
        )
        self.client.force_login(self.user)

    def post_edit(
        self,
        booking,
        start,
        end,
        payment_method='cash',
        tariff=None,
    ):
        data = {
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M'),
            'tariff': tariff.pk if tariff else booking.tariff_id,
        }
        if payment_method is not None:
            data['payment_method'] = payment_method
        return self.client.post(
            reverse('edit_my_booking', args=[booking.pk]),
            data,
        )

    def test_owner_can_update_times_and_payment_method_in_database(self):
        new_start = (
            self.start + timedelta(hours=4)
        ).replace(second=0, microsecond=0)
        new_end = new_start + timedelta(hours=3)

        response = self.post_edit(
            self.booking,
            new_start,
            new_end,
            payment_method='card',
        )

        self.assertRedirects(
            response,
            reverse('payment_result', args=[self.booking.pk]),
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.start_time, new_start)
        self.assertEqual(self.booking.end_time, new_end)
        self.assertEqual(self.booking.payment_method, 'card')

    def test_edit_is_rejected_when_another_booking_overlaps(self):
        occupied_start = self.start + timedelta(hours=4)
        Booking.objects.create(
            user=self.other_user,
            customer_name='Other Owner',
            phone='+380671234568',
            computer=self.computer,
            tariff=self.tariff,
            start_time=occupied_start,
            end_time=occupied_start + timedelta(hours=2),
            payment_method='cash',
        )

        response = self.post_edit(
            self.booking,
            occupied_start + timedelta(minutes=30),
            occupied_start + timedelta(hours=1),
            payment_method='card',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'немає вільного комп’ютера')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.start_time, self.start)
        self.assertEqual(self.booking.payment_method, 'cash')

    def test_user_cannot_edit_another_users_booking(self):
        self.client.force_login(self.other_user)

        response = self.post_edit(
            self.booking,
            self.start + timedelta(hours=4),
            self.start + timedelta(hours=5),
        )

        self.assertEqual(response.status_code, 404)

    def test_end_time_must_be_after_start_time(self):
        response = self.post_edit(
            self.booking,
            self.start + timedelta(hours=4),
            self.start + timedelta(hours=3),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Час завершення має бути пізніше за час початку.',
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.start_time, self.start)

    def test_owner_can_change_tariff_when_computer_is_available(self):
        pro_tariff = Tariff.objects.create(
            name='PRO',
            price_per_hour=80,
        )
        pro_computer = Computer.objects.create(
            name='Computer pro',
            status='available',
        )

        response = self.post_edit(
            self.booking,
            self.start + timedelta(hours=4),
            self.start + timedelta(hours=6),
            tariff=pro_tariff,
        )

        self.assertRedirects(response, reverse('my_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.tariff, pro_tariff)
        self.assertEqual(self.booking.computer, pro_computer)

    def test_paid_booking_can_change_tariff_without_posting_disabled_payment(self):
        self.booking.payment_status = 'paid'
        self.booking.save(update_fields=['payment_status'])
        pro_tariff = Tariff.objects.create(
            name='PRO',
            price_per_hour=80,
        )
        pro_computer = Computer.objects.create(
            name='Computer pro',
            status='available',
        )

        response = self.post_edit(
            self.booking,
            self.start + timedelta(hours=4),
            self.start + timedelta(hours=6),
            payment_method=None,
            tariff=pro_tariff,
        )

        self.assertRedirects(response, reverse('my_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.tariff, pro_tariff)
        self.assertEqual(self.booking.computer, pro_computer)
        self.assertEqual(self.booking.payment_method, 'cash')
        self.assertEqual(self.booking.payment_status, 'paid')

    def test_tariff_change_is_rejected_when_no_computer_is_available(self):
        pro_tariff = Tariff.objects.create(
            name='PRO',
            price_per_hour=80,
        )
        pro_computer = Computer.objects.create(
            name='Computer pro',
            status='available',
        )
        Booking.objects.create(
            user=self.other_user,
            customer_name='Other Owner',
            phone='+380671234568',
            computer=pro_computer,
            tariff=pro_tariff,
            start_time=self.start + timedelta(hours=3),
            end_time=self.start + timedelta(hours=6),
            payment_method='cash',
        )

        response = self.post_edit(
            self.booking,
            self.start + timedelta(hours=4),
            self.start + timedelta(hours=5),
            tariff=pro_tariff,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'немає вільного комп’ютера')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.tariff, self.tariff)
        self.assertEqual(self.booking.computer, self.computer)

    def test_new_booking_cannot_take_an_occupied_time_slot(self):
        UserProfile.objects.create(user=self.user, phone='+380671234567')

        response = self.client.post(reverse('booking'), {
            'name': 'Booking Owner',
            'tariff': 'default',
            'duration': '1',
            'date': self.start.strftime('%Y-%m-%d'),
            'time': self.start.strftime('%H:%M'),
            'payment_method': 'cash',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Немає вільного комп’ютера')
        self.assertEqual(Booking.objects.count(), 1)


class BookingCardPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='card-owner',
            password='StrongPassw0rd!xyz',
        )
        self.computer = Computer.objects.create(
            name='Computer defolt',
            status='available',
        )
        self.tariff = Tariff.objects.create(
            name='DEFAULT',
            price_per_hour=50,
        )
        self.start = (
            timezone.localtime(timezone.now()) + timedelta(days=3)
        ).replace(second=0, microsecond=0)
        self.booking = Booking.objects.create(
            user=self.user,
            customer_name='Card Owner',
            phone='+380671234567',
            computer=self.computer,
            tariff=self.tariff,
            start_time=self.start,
            end_time=self.start + timedelta(hours=1),
            payment_method='cash',
        )
        self.client.force_login(self.user)

    def test_editing_payment_to_card_redirects_to_card_payment_page(self):
        response = self.client.post(
            reverse('edit_my_booking', args=[self.booking.pk]),
            {
                'start_time': self.start.strftime('%Y-%m-%dT%H:%M'),
                'end_time': (
                    self.start + timedelta(hours=2)
                ).strftime('%Y-%m-%dT%H:%M'),
                'payment_method': 'card',
                'tariff': self.booking.tariff_id,
            },
        )

        self.assertRedirects(
            response,
            reverse('payment_result', args=[self.booking.pk]),
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_method, 'card')
        self.assertEqual(self.booking.payment_status, 'unpaid')

        payment_page = self.client.get(response.url)
        self.assertEqual(payment_page.status_code, 200)
        self.assertContains(payment_page, 'Оплата карткою')

    def test_successful_card_form_marks_booking_paid_and_returns_to_bookings(self):
        self.booking.payment_method = 'card'
        self.booking.save(update_fields=['payment_method'])
        expiry = (
            timezone.localtime(timezone.now()) + timedelta(days=35)
        ).strftime('%m/%y')

        response = self.client.post(
            reverse('payment_result', args=[self.booking.pk]),
            {
                'card_number': '4242 4242 4242 4242',
                'card_name': 'CARD OWNER',
                'expiry': expiry,
                'cvc': '123',
            },
        )

        self.assertRedirects(response, reverse('my_bookings'))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, 'paid')
        self.assertEqual(self.booking.payment_method, 'card')
        self.assertContains(self.client.get(reverse('my_bookings')), 'ОПЛАЧЕНО')

    def test_invalid_card_data_does_not_mark_booking_paid(self):
        self.booking.payment_method = 'card'
        self.booking.save(update_fields=['payment_method'])

        response = self.client.post(
            reverse('payment_result', args=[self.booking.pk]),
            {
                'card_number': '123',
                'card_name': 'CARD OWNER',
                'expiry': '01/20',
                'cvc': '12',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, 'unpaid')
        self.assertContains(response, 'Введіть номер картки з 16 цифр.')

    def test_payment_card_fields_are_validated_server_side(self):
        form = PaymentCardForm(data={
            'card_number': '１２３４５６７８９０１２３４５６',
            'card_name': 'CARD OWNER',
            'expiry': '12/39',
            'cvc': '123',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('card_number', form.errors)
=======
from django.test import TestCase

# Create your tests here.
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
