import re

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
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
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
                cleaned_data.get('start_time') != self.booking.start_time
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

class CustomUserCreationForm(forms.ModelForm):
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
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        strip=False,
        min_length=8,
        help_text='Пароль має містити щонайменше 8 символів.',
    )

    class Meta:
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = ''
        self.fields['email'].label = 'Електронна пошта'
        self.fields['email'].required = False
        self.fields['email'].widget.attrs['autocomplete'] = 'email'

    def clean(self):
        cleaned_data = super().clean()
        clean_phone_fields(self)
        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data.get('password')
        user = User(
            username=self.cleaned_data.get('username')
        )

        try:
            validate_password(password, user=user)
        except ValidationError as error:
            raise forms.ValidationError(error.messages)

        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'phone': self.cleaned_data['phone']},
            )

        return user
