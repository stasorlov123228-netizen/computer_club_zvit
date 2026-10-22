import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from .models import Booking


class BookingModelForm(forms.ModelForm):
    """Editable booking fields; ownership and payment state stay server-side."""

    class Meta:
        model = Booking
        fields = (
            'customer_name',
            'phone',
            'computer',
            'tariff',
            'start_time',
            'end_time',
        )
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M',
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M',
            ),
        }
        labels = {
            'customer_name': 'Ім’я клієнта',
            'phone': 'Телефон',
            'computer': 'Комп’ютер',
            'tariff': 'Тариф',
            'start_time': 'Час початку',
            'end_time': 'Час завершення',
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = re.sub(r'[\s()\-]', '', phone)
        if digits.startswith('0') and len(digits) == 10:
            digits = '+38' + digits
        elif digits.startswith('380'):
            digits = '+' + digits
        if not re.fullmatch(r'\+380\d{9}', digits):
            raise ValidationError(
                'Введіть коректний український номер телефону у форматі '
                '+380XXXXXXXXX або 0XXXXXXXXX.'
            )
        return digits

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        computer = cleaned.get('computer')
        if self.instance.pk and self.instance.payment_status == 'paid':
            self.add_error(None, 'Оплачене бронювання не можна редагувати.')
        if start and start <= timezone.now():
            self.add_error(
                'start_time',
                'Час початку має бути в майбутньому.',
            )
        if start and end and end <= start:
            self.add_error(
                'end_time', 'Час завершення має бути пізніше за час початку.',
            )
        if computer:
            if computer.status == 'maintenance' or computer.manual_occupied:
                self.add_error('computer', 'Цей комп’ютер зараз недоступний.')
            elif start and end and end > start:
                conflicts = Booking.objects.filter(
                    computer=computer, start_time__lt=end, end_time__gt=start,
                ).exclude(status='cancelled')
                if self.instance.pk:
                    conflicts = conflicts.exclude(pk=self.instance.pk)
                if conflicts.exists():
                    self.add_error(
                        'computer',
                        'Цей комп’ютер уже заброньований на обраний час.',
                    )
        return cleaned

import re
from datetime import timedelta

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Exists, IntegerField, OuterRef, When
from django.utils import timezone

from .models import Booking, Computer, Tariff, UserProfile
from .phone_numbers import PHONE_COUNTRY_CHOICES, PHONE_COUNTRIES, validate_phone_number
from .services import (
    BOOKING_DURATION_CHOICES, booking_duration_choices,
    booking_duration_value, duration_as_timedelta,
)


def clean_phone_fields(form):
    country_code = form.cleaned_data.get('phone_country')
    local_number = form.cleaned_data.get('phone_local', '').strip()
    if country_code:
        try:
            form.cleaned_data['phone'] = validate_phone_number(
                country_code, local_number,
            )
        except ValidationError as error:
            form.add_error('phone_local', error)
    return form.cleaned_data



class CardPaymentForm(forms.Form):
    """Validates transient card details for the local payment simulation."""

    card_number = forms.CharField(max_length=19, strip=True)
    cardholder_name = forms.CharField(max_length=100, strip=True)
    expiry = forms.CharField(max_length=5, strip=True)
    cvc = forms.CharField(max_length=3, strip=True)

    def clean_card_number(self):
        number = self.cleaned_data['card_number']
        if not re.fullmatch(r'[0-9 ]+', number):
            raise ValidationError(
                'Введіть номер картки цифрами, використовуючи лише пробіли між групами.'
            )
        digits = number.replace(' ', '')
        if not 13 <= len(digits) <= 16:
            raise ValidationError(
                'Номер картки має містити від 13 до 16 цифр.'
            )
        return digits

    def clean_cardholder_name(self):
        name = self.cleaned_data['cardholder_name'].strip()
        if not 2 <= len(name) <= 100 or not all(
            char.isalpha() or char == ' ' for char in name
        ):
            raise ValidationError(
                'Введіть ім’я власника картки літерами та пробілами (від 2 до 100 символів).'
            )
        return name

    def clean_expiry(self):
        value = self.cleaned_data['expiry']
        match = re.fullmatch(r'(0[1-9]|1[0-2])/([0-9]{2})', value)
        if not match:
            raise ValidationError(
                'Введіть термін дії у форматі MM/YY, де місяць від 01 до 12.'
            )
        month, year = int(match.group(1)), 2000 + int(match.group(2))
        if date(year, month, 1) < timezone.localdate().replace(day=1):
            raise ValidationError(
                'Термін дії картки вже минув.'
            )
        return value

    def clean_cvc(self):
        cvc = self.cleaned_data['cvc']
        if not re.fullmatch(r'[0-9]{3}', cvc):
            raise ValidationError(
                'CVC/CVV має містити рівно 3 цифри.'
            )
        return cvc


class BookingEditForm(forms.Form):
    tariff = forms.ModelChoiceField(
        label='Тариф',
        queryset=Tariff.objects.all(),
        empty_label=None,
    )
    start_time = forms.DateTimeField(
        label='Початок',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local', 'required': True},
        ),
    )
    duration = forms.ChoiceField(
        label='Тривалість',
        choices=BOOKING_DURATION_CHOICES,
    )
    payment_method = forms.ChoiceField(
        label='Спосіб оплати',
        choices=(
            ('cash', 'Оплата на місці'),
            ('card', 'Оплата карткою'),
        ),
    )

    def __init__(self, *args, booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking
        self.fields['duration'].choices = booking_duration_choices(booking)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        if start and start <= timezone.now():
            self.add_error(
                'start_time',
                'Оберіть час початку в майбутньому.',
            )
        return cleaned_data

class AdminBookingEditForm(forms.Form):
    computer = forms.ModelChoiceField(
        label='ПК',
        queryset=Computer.objects.none(),
        empty_label=None,
    )
    tariff = forms.ModelChoiceField(
        label='Тариф',
        queryset=Tariff.objects.all().order_by('name'),
        empty_label=None,
    )
    start_time = forms.DateTimeField(
        label='Початок',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local', 'required': True},
        ),
    )
    duration = forms.ChoiceField(
        label='Тривалість',
        choices=BOOKING_DURATION_CHOICES,
    )
    payment_method = forms.ChoiceField(
        label='Оплата',
        choices=Booking.PAYMENT_METHOD_CHOICES,
    )
    payment_status = forms.ChoiceField(
        label='Статус оплати',
        choices=Booking.PAYMENT_STATUS_CHOICES,
    )
    status = forms.ChoiceField(
        label='Статус бронювання',
        choices=Booking.STATUS_CHOICES,
    )

    def __init__(self, *args, booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['duration'].choices = booking_duration_choices(booking)
        start = booking.start_time if booking else None
        duration = booking_duration_value(booking) if booking else None

        if self.is_bound:
            try:
                start = self.fields['start_time'].clean(
                    self.data.get('start_time', '')
                )
                duration = self.fields['duration'].clean(
                    self.data.get('duration', '')
                )
            except ValidationError:
                start = booking.start_time if booking else None
                duration = (
                    booking_duration_value(booking) if booking else None
                )

        end = (
            start + duration_as_timedelta(duration)
            if start and duration
            else None
        )

        computers = Computer.objects.filter(
            manual_occupied=False,
        ).exclude(status='maintenance')
        if booking and start and end and end > start:
            conflicting_bookings = Booking.objects.filter(
                computer_id=OuterRef('pk'),
                start_time__lt=end,
                end_time__gt=start,
            ).exclude(
                status='cancelled',
            ).exclude(
                pk=booking.pk,
            )
            computers = computers.annotate(
                has_conflict=Exists(conflicting_bookings),
            ).filter(has_conflict=False)

        def computer_sort_key(computer):
            number = re.search(r'\d+', computer.name)
            return (
                int(number.group()) if number else float('inf'),
                computer.name.casefold(),
                computer.pk,
            )

        ordered_computers = sorted(computers, key=computer_sort_key)
        computer_ids = [
            computer.pk for computer in ordered_computers
        ]
        if computer_ids:
            computers = computers.filter(
                pk__in=computer_ids,
            ).order_by(Case(
                *[
                    When(pk=computer_id, then=position)
                    for position, computer_id in enumerate(computer_ids)
                ],
                output_field=IntegerField(),
            ))
        self.fields['computer'].queryset = computers
        self.fields['computer'].choices = [
            (computer.pk, str(computer))
            for computer in ordered_computers
        ]
        self.booking = booking

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        payment_status = cleaned_data.get('payment_status')
        status = cleaned_data.get('status')
        if self.booking and self.booking.payment_status == 'paid':
            if (
                cleaned_data.get('computer') != self.booking.computer
                or cleaned_data.get('start_time') != self.booking.start_time
                or (
                    cleaned_data.get('duration')
                    != booking_duration_value(self.booking)
                )
                or cleaned_data.get('tariff') != self.booking.tariff
            ):
                self.add_error(
                    None,
                    'Параметри оплаченого бронювання змінювати не можна.',
                )
            if payment_method != self.booking.payment_method:
                self.add_error(
                    'payment_method',
                    'Спосіб оплати оплаченого бронювання змінювати не можна.',
                )
            if payment_status != 'paid':
                self.add_error(
                    'payment_status',
                    'Статус оплати можна змінити лише після підтвердження повернення.',
                )
            if status != 'confirmed':
                self.add_error(
                    'status',
                    'Оплачене бронювання не можна скасувати або повернути в очікування.',
                )
        if (
            payment_method == 'card'
            and payment_status != 'paid'
            and status == 'confirmed'
        ):
            cleaned_data['status'] = 'pending'
        selected_id = self.data.get('computer') if self.is_bound else None
        try:
            selected_pk = Computer._meta.pk.to_python(selected_id)
        except (ValidationError, ValueError):
            selected_pk = None
        computer = (
            Computer.objects.filter(pk=selected_pk).first()
            if selected_pk is not None
            else None
        )
        if selected_id and 'computer' not in cleaned_data and computer:
            if computer.status == 'maintenance' or computer.manual_occupied:
                message = 'Цей ПК зараз недоступний.'
            else:
                message = 'ПК уже заброньований на обраний час.'
            self.add_error('computer', message)
        return cleaned_data

class EmailForm(forms.Form):
    email = forms.EmailField(
        label='Електронна пошта',
        required=False,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
        }),
    )

class PhoneNumberForm(forms.Form):
    phone_country = forms.ChoiceField(
        label='Код країни',
        choices=PHONE_COUNTRY_CHOICES,
    )
    phone_local = forms.CharField(
        label='Номер телефону',
        widget=forms.TextInput(attrs={
            'type': 'tel',
            'inputmode': 'numeric',
            'autocomplete': 'tel-national',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        clean_phone_fields(self)
        return cleaned_data

class CustomUserCreationForm(UserCreationForm):
    phone_country = forms.ChoiceField(
        label='Код країни',
        choices=PHONE_COUNTRY_CHOICES,
    )
    phone_local = forms.CharField(
        label='Номер телефону',
        widget=forms.TextInput(attrs={
            'type': 'tel',
            'inputmode': 'numeric',
            'autocomplete': 'tel-national',
        }),
    )
    class Meta:
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Ім’я користувача'
        self.fields['username'].help_text = ''
        self.fields['email'].label = 'Електронна пошта'
        self.fields['email'].required = False
        self.fields['email'].widget.attrs['autocomplete'] = 'email'
        self.fields['password1'].label = 'Пароль'
        self.fields['password1'].help_text = (
            'Введіть пароль, який відповідає вимогам безпеки.'
        )
        self.fields['password2'].label = 'Підтвердження пароля'
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'

    def clean(self):
        cleaned_data = super().clean()
        clean_phone_fields(self)
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exclude(
            pk=self.instance.pk,
        ).exists():
            raise forms.ValidationError(
                '\u0426\u0435\u0439 \u043b\u043e\u0433\u0456\u043d \u0443\u0436\u0435 \u0437\u0430\u0439\u043d\u044f\u0442\u0438\u0439. \u0411\u0443\u0434\u044c \u043b\u0430\u0441\u043a\u0430, \u043e\u0431\u0435\u0440\u0456\u0442\u044c \u0456\u043d\u0448\u0438\u0439'
            )
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            with transaction.atomic():
                user.save()
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={'phone': self.cleaned_data['phone']},
                )

        return user
