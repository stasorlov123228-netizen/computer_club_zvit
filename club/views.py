
from datetime import datetime, timedelta
<<<<<<< HEAD
import re
from django.contrib.auth.decorators import login_required, user_passes_test
=======
from django.contrib.auth.decorators import login_required
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
from django import forms
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
<<<<<<< HEAD
from django.db import transaction
from django.db.models import (
    Case,
    Exists,
    IntegerField,
    OuterRef,
    Q,
    When,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Computer, Tariff, Booking, Payment, UserProfile
from .phone_numbers import (
    PHONE_COUNTRIES,
    PHONE_COUNTRY_CHOICES,
    split_phone_number,
    validate_phone_number,
)
=======
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Computer, Tariff, Booking, Payment
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1



def update_computer_statuses():
    now = timezone.now()

    computers = Computer.objects.exclude(status='maintenance')

    for computer in computers:
        is_occupied = computer.manual_occupied or Booking.objects.filter(
            computer=computer,
            status='confirmed',
            start_time__lte=now,
            end_time__gt=now,
        ).exists()

        new_status = 'occupied' if is_occupied else 'available'

        if computer.status != new_status:
            Computer.objects.filter(pk=computer.pk).update(
                status=new_status
            )


def home(request):
    update_computer_statuses()

    context = {
        'total_computers': Computer.objects.count(),
        'available_computers': Computer.objects.filter(
            status='available'
        ).count(),
        'occupied_computers': Computer.objects.filter(
            status='occupied'
        ).count(),
        'total_clients': User.objects.count(),
    }

    return render(request, 'club/home.html', context)



@login_required
def account_view(request):
<<<<<<< HEAD
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST' and 'update_phone' in request.POST:
        phone_form = PhoneNumberForm(request.POST)
        if phone_form.is_valid():
            profile.phone = phone_form.cleaned_data['phone']
            profile.save(update_fields=['phone'])
            return redirect('account')
    else:
        _, country_code, local_number = split_phone_number(profile.phone)
        phone_form = PhoneNumberForm(initial={
            'phone_country': country_code,
            'phone_local': local_number,
        })

    return render(request, 'club/account.html', {
        'phone_form': phone_form,
    })
=======
    return render(request, 'club/account.html')

>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1




@login_required
def my_bookings(request):
    update_computer_statuses()

<<<<<<< HEAD
    return render_my_bookings(request)


def render_my_bookings(request, editing_booking_id=None, edit_form=None):
    bookings = list(
        Booking.objects.filter(
            user=request.user
        ).select_related(
            'computer', 'tariff'
        ).order_by('-created_at')
    )
    booking_rows = []
    now = timezone.now()
    for booking_record in bookings:
        form = None
        if booking_record.status != 'cancelled' and booking_record.start_time > now:
            if booking_record.id == editing_booking_id and edit_form is not None:
                form = edit_form
            else:
                form = BookingEditForm(
                    initial={
                        'start_time': booking_record.start_time,
                        'end_time': booking_record.end_time,
                        'payment_method': booking_record.payment_method,
                        'tariff': booking_record.tariff_id,
                    }
                )
            if booking_record.payment_status == 'paid':
                lock_booking_payment_method(form, booking_record)
        booking_rows.append((booking_record, form))

    return render(request, 'club/my_bookings.html', {
        'bookings': bookings,
        'booking_rows': booking_rows,
        'editing_booking_id': editing_booking_id,
    })


def lock_booking_payment_method(form, booking_record):
    form.fields['payment_method'].disabled = True
    form.initial['payment_method'] = booking_record.payment_method
    form.fields['payment_method'].help_text = (
        'Спосіб оплати не можна змінити після оплати.'
    )


def find_available_computer(tariff_code, start, end, exclude_booking_id=None):
    computer_suffixes = {
        'default': 'defolt',
        'pro': 'pro',
        'vip': 'vip',
        'stream': 'stream',
    }
    suffix = computer_suffixes[tariff_code]
    candidates = Computer.objects.filter(
        name__iendswith=suffix,
        manual_occupied=False,
    ).exclude(status='maintenance').order_by('id')

    for candidate in candidates:
        computer = Computer.objects.select_for_update().get(pk=candidate.pk)
        conflicts = Booking.objects.filter(
            computer=computer,
            start_time__lt=end,
            end_time__gt=start,
        ).exclude(status='cancelled')
        if exclude_booking_id is not None:
            conflicts = conflicts.exclude(pk=exclude_booking_id)
        if not conflicts.exists():
            return computer

    return None


@login_required
@require_POST
def edit_my_booking(request, booking_id):
    booking_record = get_object_or_404(
        Booking,
        pk=booking_id,
        user=request.user,
    )
    form = BookingEditForm(request.POST)
    if booking_record.payment_status == 'paid':
        lock_booking_payment_method(form, booking_record)

    if not form.is_valid():
        return render_my_bookings(request, booking_id, form)

    needs_payment = False
    with transaction.atomic():
        booking_record = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
            user=request.user,
        )
        if (
            booking_record.status == 'cancelled'
            or booking_record.start_time <= timezone.now()
        ):
            form.add_error(
                None,
                'Це бронювання вже не можна редагувати.',
            )
        else:
            start = form.cleaned_data['start_time']
            end = form.cleaned_data['end_time']
            tariff = form.cleaned_data['tariff']
            if start <= timezone.now():
                form.add_error(
                    'start_time',
                    'Оберіть час початку в майбутньому.',
                )
            elif end <= start:
                form.add_error(
                    'end_time',
                    'Час завершення має бути пізніше за час початку.',
                )
            else:
                tariff_codes = {
                    'DEFAULT': 'default',
                    'PRO': 'pro',
                    'VIP': 'vip',
                    'STREAM': 'stream',
                }
                tariff_code = tariff_codes.get(tariff.name.upper())
                computer = (
                    find_available_computer(
                        tariff_code,
                        start,
                        end,
                        exclude_booking_id=booking_record.pk,
                    )
                    if tariff_code
                    else None
                )
                if not computer:
                    form.add_error(
                        'tariff',
                        'Для цього тарифу немає вільного комп’ютера '
                        'на обраний час.',
                    )
                else:
                    booking_record.start_time = start
                    booking_record.end_time = end
                    booking_record.tariff = tariff
                    booking_record.computer = computer
                    if booking_record.payment_status != 'paid':
                        booking_record.payment_method = (
                            form.cleaned_data['payment_method']
                        )
                    booking_record.save(update_fields=[
                        'start_time',
                        'end_time',
                        'payment_method',
                        'tariff',
                        'computer',
                    ])
                    needs_payment = (
                        booking_record.payment_method == 'card'
                        and booking_record.payment_status != 'paid'
                    )

    if form.errors:
        return render_my_bookings(request, booking_id, form)

    if needs_payment:
        return redirect('payment_result', booking_id=booking_id)

    return redirect('my_bookings')

def booking(request):
    profile = None
    phone = ''
    if request.user.is_authenticated:
        profile = UserProfile.objects.filter(user=request.user).first()
        phone = profile.phone if profile else ''

    iso, phone_country, saved_local_number = split_phone_number(phone)
    phone_local = (
        request.POST.get('phone_local', '').strip()
        if request.method == 'POST' and not request.user.is_authenticated
        else saved_local_number
    )
    context = {
        'errors': [],
        'phone_countries': [list(country) for country in PHONE_COUNTRIES],
        'phone_country': phone_country,
        'phone_iso': iso,
        'phone_local': phone_local,
        'phone_required': not request.user.is_authenticated,
        'missing_profile_phone': (
            request.user.is_authenticated and not phone
        ),
    }

    if request.method != 'POST':
        return render(request, 'club/booking.html', context)
=======
    bookings = Booking.objects.filter(
        user=request.user
    ).select_related(
        'computer', 'tariff'
    ).order_by('-created_at')

    return render(request, 'club/my_bookings.html', {
        'bookings': bookings,
    })

def booking(request):
    if request.method != 'POST':
        return render(request, 'club/booking.html', {'errors': []})
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1

    errors = []
    name = request.POST.get('name', '').strip()
    tariff_code = request.POST.get('tariff', '').strip()
    duration_value = request.POST.get('duration', '').strip()
    date_value = request.POST.get('date', '').strip()
    time_value = request.POST.get('time', '').strip()
    payment_method = request.POST.get('payment_method', '').strip()
<<<<<<< HEAD

    if request.user.is_authenticated:
        if not phone:
            errors.append(
                'У профілі не вказаний номер телефону. '
                'Додайте його в акаунті перед бронюванням.'
            )
    else:
        phone_country = request.POST.get('phone_country', '').strip()
        phone_local = request.POST.get('phone_local', '').strip()
        try:
            phone = validate_phone_number(phone_country, phone_local)
        except ValidationError as error:
            errors.extend(error.messages)

    if not name:
        errors.append("Введіть ім’я.")

    tariff_names = {
        'default': 'DEFAULT',
        'pro': 'PRO',
        'vip': 'VIP',
        'stream': 'STREAM',
    }
    if tariff_code not in tariff_names:
        errors.append('Оберіть правильний тариф.')
    if duration_value not in ('1', '2', '3', '5', '8'):
        errors.append('Оберіть тривалість бронювання.')
    if payment_method not in ('card', 'cash'):
        errors.append('Оберіть спосіб оплати.')

    start = None
    end = None
    try:
        if duration_value not in ('1', '2', '3', '5', '8'):
            raise ValueError
        duration = int(duration_value)
        start = datetime.strptime(
            f'{date_value} {time_value}',
            '%Y-%m-%d %H:%M'
        )
        start = timezone.make_aware(
            start,
            timezone.get_current_timezone()
        )
        end = start + timedelta(hours=duration)
    except (ValueError, TypeError):
        if 'Оберіть тривалість бронювання.' not in errors:
            errors.append('Перевірте дату та час.')

    if start and start <= timezone.now():
        errors.append('Оберіть час у майбутньому.')

    tariff = None
    computer = None
    booking_record = None
    if not errors:
        tariff = Tariff.objects.filter(
            name__iexact=tariff_names[tariff_code]
        ).first()
        if not tariff:
            errors.append('Цей тариф ще не доданий в адмінпанелі.')

    if not errors:
        with transaction.atomic():
            computer = find_available_computer(
                tariff_code,
                start,
                end,
            )
=======
    phone_country = request.POST.get('phone_country', '+380').strip()
    phone_local = request.POST.get('phone_local', '').strip()

    # Код країни: (мінімум цифр, максимум цифр) у номері без коду країни
    phone_rules = {
        '+380': (9, 9),   '+1': (10, 10),   '+44': (10, 10),
        '+48': (9, 9),    '+49': (10, 11),  '+33': (9, 9),
        '+39': (9, 10),   '+34': (9, 9),    '+420': (9, 9),
        '+421': (9, 9),   '+40': (9, 9),    '+373': (8, 8),
        '+43': (10, 11),  '+41': (9, 9),    '+31': (9, 9),
        '+32': (8, 9),    '+351': (9, 9),   '+30': (10, 10),
        '+359': (8, 9),   '+385': (8, 9),   '+386': (8, 8),
        '+36': (9, 9),    '+370': (8, 8),   '+371': (8, 8),
        '+372': (7, 8),   '+358': (9, 10),  '+46': (9, 9),
        '+47': (8, 8),    '+45': (8, 8),    '+354': (7, 7),
        '+353': (9, 9),   '+90': (10, 10),  '+995': (9, 9),
        '+374': (8, 8),   '+994': (9, 9),   '+7': (10, 10),
        '+81': (10, 10),  '+82': (9, 10),   '+86': (11, 11),
        '+91': (10, 10),  '+92': (10, 10),  '+880': (10, 10),
        '+66': (9, 9),    '+84': (9, 10),   '+60': (9, 10),
        '+65': (8, 8),    '+62': (9, 11),   '+63': (10, 10),
        '+972': (9, 9),   '+971': (9, 9),   '+966': (9, 9),
        '+20': (10, 10),  '+27': (9, 9),    '+234': (10, 10),
        '+254': (9, 9),   '+212': (9, 9),   '+55': (10, 11),
        '+54': (10, 10),  '+56': (9, 9),    '+57': (10, 10),
        '+52': (10, 10),  '+61': (9, 9),    '+64': (8, 9),
    }

    country_digits = ''.join(filter(str.isdigit, phone_country))
    local_digits = ''.join(filter(str.isdigit, phone_local))
    phone = f'+{country_digits}{local_digits}'

    if phone_country not in phone_rules:
        errors.append('Оберіть країну зі списку.')
    elif not phone_local:
        errors.append('Введіть номер телефону.')
    elif not phone_local.isdigit():
        errors.append('Номер телефону повинен містити лише цифри.')
    else:
        min_len, max_len = phone_rules[phone_country]

        if not (min_len <= len(phone_local) <= max_len):
            if min_len == max_len:
                expected = f'{min_len}'
            else:
                expected = f'{min_len}–{max_len}'

            errors.append(
                f'Для {phone_country} номер має містити '
                f'{expected} цифр після коду країни.'
            )

        if not name:
            errors.append("Введіть ім’я.")

        tariff_names = {
            'default': 'DEFAULT',
            'pro': 'PRO',
            'vip': 'VIP',
            'stream': 'STREAM',
        }

        computer_suffixes = {
            'default': 'defolt',
            'pro': 'pro',
            'vip': 'vip',
            'stream': 'stream',
        }

        if tariff_code not in tariff_names:
            errors.append('Оберіть правильний тариф.')

        if duration_value not in ('1', '2', '3', '5', '8'):
            errors.append('Оберіть тривалість бронювання.')

        if payment_method not in ('card', 'cash'):
            errors.append('Оберіть спосіб оплати.')

        start = None
        end = None

        try:
            duration = int(duration_value)

            if duration_value not in ('1', '2', '3', '5', '8'):
                raise ValueError

            start = datetime.strptime(
                f'{date_value} {time_value}',
                '%Y-%m-%d %H:%M'
            )

            start = timezone.make_aware(
                start,
                timezone.get_current_timezone()
            )

            end = start + timedelta(hours=duration)

        except (ValueError, TypeError):
            if 'Оберіть тривалість бронювання.' not in errors:
                errors.append('Перевірте дату та час.')

        if start and start <= timezone.now():
            errors.append('Оберіть час у майбутньому.')

        tariff = None
        computer = None

        if not errors:
            tariff = Tariff.objects.filter(
                name__iexact=tariff_names[tariff_code]
            ).first()

            if not tariff:
                errors.append(
                    'Цей тариф ще не доданий в адмінпанелі.'
                )

        if not errors:
            computer = Computer.objects.filter(
                status='available',
                name__iendswith=computer_suffixes[tariff_code]
            ).exclude(
                booking__start_time__lt=end,
                booking__end_time__gt=start,
                booking__status='cancelled',
            ).order_by('id').first()

>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
            if not computer:
                errors.append(
                    'Немає вільного комп’ютера для цього тарифу '
                    'на вибраний час.'
                )
<<<<<<< HEAD
            else:
                booking_record = Booking.objects.create(
                    user=(
                        request.user
                        if request.user.is_authenticated
                        else None
                    ),
                    customer_name=name,
                    phone=phone,
                    tariff=tariff,
                    computer=computer,
                    start_time=start,
                    end_time=end,
                    payment_method=payment_method,
                    payment_status='unpaid',
                )

    if booking_record:
        if payment_method == 'card':
            return redirect(
                'payment_result',
                booking_id=booking_record.id
            )

        return render(
            request,
            'club/booking_success.html',
            {'booking': booking_record}
        )

    context.update({
        'errors': errors,
        'phone_country': request.POST.get('phone_country', phone_country),
        'phone_iso': request.POST.get('phone_iso', iso),
        'phone_local': request.POST.get('phone_local', phone_local),
    })
    return render(request, 'club/booking.html', context)
=======

        if not errors:
            booking_record = Booking.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=name,
                phone=phone,
                tariff=tariff,
                computer=computer,
                start_time=start,
                end_time=end,
                payment_method=payment_method,
                payment_status='unpaid',
            )

            # Якщо карткою — переходимо до форми оплати
            if payment_method == 'card':
                return redirect(
                    'payment_result',
                    booking_id=booking_record.id
                )

            # Якщо готівкою — показуємо успішне бронювання
            return render(
                request,
                'club/booking_success.html',
                {'booking': booking_record}
            )

    return render(
        request,
        'club/booking.html',
        {'errors': errors}
    )
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1

    



def login_view(request):
    if request.user.is_authenticated:
<<<<<<< HEAD
=======
        if request.user.username == 'admin':
            return redirect('admin_panel')
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
        return redirect('home')

    form = AuthenticationForm(
        request,
        data=request.POST or None
    )

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
<<<<<<< HEAD
=======

        if user.username == 'admin':
            return redirect('admin_panel')

>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
        return redirect('home')

    return render(request, 'club/login.html', {'form': form})


<<<<<<< HEAD
def clean_phone_fields(form):
    country_code = form.cleaned_data.get('phone_country')
    local_number = form.cleaned_data.get('phone_local', '').strip()
    if country_code:
        try:
            form.cleaned_data['phone'] = validate_phone_number(
                country_code,
                local_number,
            )
        except ValidationError as error:
            form.add_error('phone_local', error)
    return form.cleaned_data


class PaymentCardForm(forms.Form):
    card_number = forms.CharField(
        label='Номер картки',
        widget=forms.TextInput(attrs={
            'id': 'card-number',
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'placeholder': '0000 0000 0000 0000',
            'maxlength': '19',
            'required': True,
        }),
    )
    card_name = forms.CharField(
        label='Ім’я платника',
        max_length=100,
        widget=forms.TextInput(attrs={
            'id': 'card-name',
            'autocomplete': 'off',
            'placeholder': 'ІМ’Я ПРІЗВИЩЕ',
            'required': True,
        }),
    )
    expiry = forms.CharField(
        label='Термін дії',
        widget=forms.TextInput(attrs={
            'id': 'expiry',
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'placeholder': 'ММ/РР',
            'maxlength': '5',
            'required': True,
        }),
    )
    cvc = forms.CharField(
        label='CVC',
        widget=forms.PasswordInput(attrs={
            'id': 'cvc',
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'placeholder': '•••',
            'maxlength': '3',
            'required': True,
        }, render_value=False),
    )

    def clean_card_number(self):
        number = self.cleaned_data['card_number'].replace(' ', '')
        if not number.isascii() or not number.isdigit() or len(number) != 16:
            raise forms.ValidationError(
                'Введіть номер картки з 16 цифр.'
            )
        return number

    def clean_card_name(self):
        name = ' '.join(self.cleaned_data['card_name'].split())
        if (
            not name
            or not name[0].isalpha()
            or not all(
                character.isalpha() or character in " '-"
                for character in name
            )
            or not any(character.isalpha() for character in name)
        ):
            raise forms.ValidationError(
                'Введіть правильне ім’я платника.'
            )
        return name

    def clean_expiry(self):
        expiry = self.cleaned_data['expiry']
        match = re.fullmatch(r'(0[1-9]|1[0-2])/([0-9]{2})', expiry)
        if not match:
            raise forms.ValidationError(
                'Введіть дату у форматі ММ/РР. Місяць має бути від 01 до 12.'
            )
        month, year = int(match.group(1)), 2000 + int(match.group(2))
        now = timezone.localtime()
        if (year, month) < (now.year, now.month):
            raise forms.ValidationError('Термін дії картки минув.')
        return expiry

    def clean_cvc(self):
        cvc = self.cleaned_data['cvc']
        if not cvc.isascii() or not cvc.isdigit() or len(cvc) != 3:
            raise forms.ValidationError('CVC має містити рівно 3 цифри.')
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
    end_time = forms.DateTimeField(
        label='Завершення',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local', 'required': True},
        ),
    )
    payment_method = forms.ChoiceField(
        label='Спосіб оплати',
        choices=(
            ('cash', 'Оплата на місці'),
            ('card', 'Оплата карткою'),
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and start <= timezone.now():
            self.add_error(
                'start_time',
                'Оберіть час початку в майбутньому.',
            )
        if start and end and end <= start:
            self.add_error(
                'end_time',
                'Час завершення має бути пізніше за час початку.',
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
    end_time = forms.DateTimeField(
        label='Завершення',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={'type': 'datetime-local', 'required': True},
        ),
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
        start = booking.start_time if booking else None
        end = booking.end_time if booking else None

        if self.is_bound:
            try:
                start = self.fields['start_time'].clean(
                    self.data.get('start_time', '')
                )
                end = self.fields['end_time'].clean(
                    self.data.get('end_time', '')
                )
            except ValidationError:
                start = booking.start_time if booking else None
                end = booking.end_time if booking else None

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
=======
class CustomUserCreationForm(forms.ModelForm):
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        strip=False,
        min_length=8,
        help_text='Пароль має містити щонайменше 8 символів.',
    )

    class Meta:
        model = User
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = ''

<<<<<<< HEAD
    def clean(self):
        cleaned_data = super().clean()
        clean_phone_fields(self)
        return cleaned_data

=======
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
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
<<<<<<< HEAD
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'phone': self.cleaned_data['phone']},
            )
=======
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1

        return user


<<<<<<< HEAD


=======
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = CustomUserCreationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('home')

<<<<<<< HEAD
    return render(request, 'club/register.html', {
        'form': form,
        'phone_countries': [list(country) for country in PHONE_COUNTRIES],
    })
=======
    return render(request, 'club/register.html', {'form': form})
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1


@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')


def tournaments_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'tournaments',
        'title': 'Турніри',
        'tournaments': [
            {
                'game': 'CS2',
                'name': 'Lviv Arena Cup',
                'format': '5 на 5'
            },
            {
                'game': 'Dota 2',
                'name': 'Arena Battle',
                'format': '5 на 5'
            },
            {
                'game': 'VALORANT',
                'name': 'Valorant Challenge',
                'format': '5 на 5'
            },
            {
                'game': 'World of Tanks',
                'name': 'Tank Masters',
                'format': 'Командний турнір'
            },
        ],
    })


def news_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'news',
        'title': 'Новини клубу',
        'news': [
            {
                'title': 'Lviv Arena відкриває двері!',
                'text': 'Знайомся з новим місцем для геймерів у Львові.',
                'date': '14 жовтня 2026',
            },
            {
                'title': '55 ігрових комп’ютерів',
                'text': 'Обирай Default, Pro, VIP або Stream-зону.',
                'date': '14 жовтня 2026',
            },
            {
                'title': 'Готуйся до турнірів',
                'text': 'Незабаром на сайті з’являтимуться нові змагання.',
                'date': '14 жовтня 2026',
            },
        ],
    })


def clubs_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'clubs',
        'title': 'Наші клуби',
    })


def feedback_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'feedback',
        'title': 'Зворотний зв’язок',
    })


def partnership_view(request):
    sent = False
    error = ''
<<<<<<< HEAD
    phone_country = '+380'
    phone_local = ''

    if request.method == 'POST':
        phone_country = request.POST.get('phone_country', '').strip()
        phone_local = request.POST.get('phone_local', '').strip()
        try:
            validate_phone_number(phone_country, phone_local)
            sent = True
        except ValidationError as validation_error:
            error = ' '.join(validation_error.messages)
=======

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()

        if phone:
            sent = True
        else:
            error = 'Будь ласка, введіть номер телефону.'
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1

    return render(request, 'club/section_page.html', {
        'page_type': 'partnership',
        'title': 'Партнерство',
        'sent': sent,
        'error': error,
<<<<<<< HEAD
        'phone_country': phone_country,
        'phone_local': phone_local,
        'phone_countries': [list(country) for country in PHONE_COUNTRIES],
=======
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
    })



def payment_result(request, booking_id):
    update_computer_statuses()

<<<<<<< HEAD
    bookings = Booking.objects.filter(id=booking_id)
    if request.user.is_authenticated:
        bookings = bookings.filter(
            Q(user=request.user) | Q(user__isnull=True)
        )
    else:
        booking_record = get_object_or_404(bookings)
        if booking_record.user_id:
            return redirect('login')
        bookings = Booking.objects.filter(pk=booking_record.pk)

    booking_record = get_object_or_404(bookings)

    if booking_record.status == 'cancelled':
        return redirect('my_bookings' if booking_record.user_id else 'home')

    if booking_record.payment_status == 'paid':
        return redirect('my_bookings' if booking_record.user_id else 'home')

    if booking_record.payment_method != 'card':
        return redirect('my_bookings' if booking_record.user_id else 'home')

    if request.method == 'POST':
        payment_form = PaymentCardForm(request.POST)
        if payment_form.is_valid():
            with transaction.atomic():
                booking_record = get_object_or_404(
                    Booking.objects.select_for_update(),
                    pk=booking_record.pk,
                )
                if (
                    booking_record.status == 'cancelled'
                    or booking_record.payment_method != 'card'
                ):
                    payment_form.add_error(
                        None,
                        'Оплату для цього бронювання завершити неможливо.',
                    )
                elif booking_record.payment_status != 'paid':
                    booking_record.payment_status = 'paid'
                    booking_record.save(update_fields=['payment_status'])

            if not payment_form.errors:
                if booking_record.user_id:
                    return redirect('my_bookings')
                return render(
                    request,
                    'club/booking_success.html',
                    {'booking': booking_record}
                )

        payment_errors = [
            error
            for errors in payment_form.errors.values()
            for error in errors
        ]
        return render(request, 'club/payment_result.html', {
            'booking': booking_record,
            'payment_form': PaymentCardForm(),
            'payment_errors': payment_errors,
        })

    return render(request, 'club/payment_result.html', {
        'booking': booking_record,
        'payment_form': PaymentCardForm(),
    })
=======
    booking_record = get_object_or_404(
        Booking,
        id=booking_id
    )

    if request.method == 'POST':
        booking_record.payment_status = 'paid'
        booking_record.save(update_fields=['payment_status'])

        update_computer_statuses()

        return render(
            request,
            'club/booking_success.html',
            {'booking': booking_record}
        )

    return render(
        request,
        'club/payment_result.html',
        {'booking': booking_record}
    )
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1



def liqpay_callback(request):
    return redirect('payment_result')

@login_required
def admin_panel(request):
<<<<<<< HEAD
    if not is_admin_or_staff(request.user):
=======
    if request.user.username != 'admin' or not request.user.is_staff:
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
        return redirect('home')

    return render(request, 'club/admin_panel.html')


<<<<<<< HEAD
def is_admin_or_staff(user):
    return user.is_authenticated and (
        user.username == 'admin' or user.is_staff
    )


@user_passes_test(is_admin_or_staff)
def admin_bookings(request):
    bookings = list(
        Booking.objects.select_related(
            'computer', 'tariff', 'user'
        ).order_by('-created_at')
    )
    booking_rows = []
    for booking_record in bookings:
        form = AdminBookingEditForm(
            initial=admin_booking_initial(booking_record),
            booking=booking_record,
        )
        booking_rows.append((booking_record, form))

    return render(request, 'club/admin_bookings.html', {
        'bookings': bookings,
        'booking_rows': booking_rows,
    })


@user_passes_test(is_admin_or_staff)
@require_POST
def edit_admin_booking(request, booking_id):
    booking_record = get_object_or_404(Booking, pk=booking_id)
    form = AdminBookingEditForm(request.POST, booking=booking_record)
    if not form.is_valid():
        return render_admin_bookings_with_error(request, booking_record, form)

    with transaction.atomic():
        booking_record = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
        )
        computer = form.cleaned_data['computer']
        tariff = form.cleaned_data['tariff']
        start = form.cleaned_data['start_time']
        end = form.cleaned_data['end_time']
        status = form.cleaned_data['status']
        computer = Computer.objects.select_for_update().get(pk=computer.pk)

        if end <= start:
            form.add_error(
                'end_time',
                'Час завершення має бути пізніше за час початку.',
            )
        elif get_pc_kind(computer.name) != get_tariff_kind(tariff.name):
            form.add_error(
                'computer',
                'Обраний ПК не відповідає вибраному тарифу.',
            )
        elif computer.status == 'maintenance' or computer.manual_occupied:
            form.add_error(
                'computer',
                'Цей ПК зараз недоступний.',
            )
        else:
            conflicts = Booking.objects.filter(
                computer=computer,
                start_time__lt=end,
                end_time__gt=start,
            ).exclude(
                pk=booking_record.pk,
            ).exclude(
                status='cancelled',
            )
            if status != 'cancelled' and conflicts.exists():
                form.add_error(
                    None,
                    'На цей час ПК уже заброньований. '
                    'Оберіть інший ПК або час.',
                )
            else:
                booking_record.computer = computer
                booking_record.tariff = tariff
                booking_record.start_time = start
                booking_record.end_time = end
                booking_record.payment_method = form.cleaned_data[
                    'payment_method'
                ]
                booking_record.payment_status = form.cleaned_data[
                    'payment_status'
                ]
                booking_record.status = status
                booking_record.save(update_fields=[
                    'computer',
                    'tariff',
                    'start_time',
                    'end_time',
                    'payment_method',
                    'payment_status',
                    'status',
                ])

    if form.errors:
        return render_admin_bookings_with_error(request, booking_record, form)

    update_computer_statuses()
    return redirect('admin_bookings')


def render_admin_bookings_with_error(request, booking_record, form):
    bookings = list(
        Booking.objects.select_related(
            'computer', 'tariff', 'user'
        ).order_by('-created_at')
    )
    booking_rows = []
    for current_booking in bookings:
        if current_booking.pk == booking_record.pk:
            current_form = form
        else:
            current_form = AdminBookingEditForm(
                initial=admin_booking_initial(current_booking),
                booking=current_booking,
            )
        booking_rows.append((current_booking, current_form))

    return render(request, 'club/admin_bookings.html', {
        'bookings': bookings,
        'booking_rows': booking_rows,
        'editing_booking_id': booking_record.pk,
    })


def admin_booking_initial(booking_record):
    return {
        'computer': booking_record.computer_id,
        'tariff': booking_record.tariff_id,
        'start_time': booking_record.start_time,
        'end_time': booking_record.end_time,
        'payment_method': booking_record.payment_method,
        'payment_status': booking_record.payment_status,
        'status': booking_record.status,
    }


def get_tariff_kind(name):
    return {
        'default': 'default',
        'pro': 'pro',
        'vip': 'vip',
        'stream': 'stream',
    }.get(name.strip().lower())


@user_passes_test(is_admin_or_staff)
def admin_users(request):
    return render(request, 'club/admin_users.html', {
        'users': User.objects.select_related(
            'profile',
        ).order_by('-date_joined'),
    })


@user_passes_test(is_admin_or_staff)
=======
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def admin_bookings(request):
    bookings = Booking.objects.select_related(
        'computer', 'tariff', 'user'
    ).order_by('-created_at')

    return render(request, 'club/admin_bookings.html', {'bookings': bookings})


@staff_member_required
def admin_users(request):
    return render(request, 'club/admin_users.html', {
        'users': User.objects.order_by('-date_joined'),
    })


@staff_member_required
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
def admin_tariffs(request):
    return render(request, 'club/admin_tariffs.html', {
        'tariffs': Tariff.objects.all(),
    })


from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from .models import Tariff


@login_required
def admin_update_tariff_price(request, tariff_id):
<<<<<<< HEAD
    if not is_admin_or_staff(request.user):
=======
    if request.user.username != 'admin' or not request.user.is_staff:
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
        return HttpResponseForbidden('Доступ заборонено.')

    if request.method != 'POST':
        return redirect('admin_tariffs')

    tariff = get_object_or_404(Tariff, pk=tariff_id)
    raw_price = request.POST.get('price', '').strip().replace(',', '.')

    try:
        new_price = Decimal(raw_price)
        if (
            not new_price.is_finite()
            or new_price < 0
            or new_price > Decimal('999999.99')
        ):
            raise InvalidOperation
        if new_price.as_tuple().exponent < -2:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return redirect('admin_tariffs')

    tariff.price_per_hour = new_price
    tariff.save(update_fields=['price_per_hour'])

    return redirect('admin_tariffs')


PC_SPECS = {
    'default': {
        'title': 'DEFAULT',
        'tier': 'Базова зона',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 5 5600'],
            ['Материнська плата', 'B550 / B660'],
            ['Оперативна пам\'ять', '16 GB DDR4 (3200–3600 MHz)'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 3060 12GB'],
            ['Накопичувач (SSD)', '512 GB NVMe M.2'],
            ['Миша', 'HyperX Pulsefire'],
            ['Клавіатура', 'Logitech G213'],
            ['Монітор', 'ASUS TUF Gaming 144 Hz'],
        ],
        'extra': [],
    },
    'pro': {
        'title': 'PRO',
        'tier': 'Для змагальних матчів',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 7 5700X3D'],
            ['Материнська плата', 'B650 / B760'],
            ['Оперативна пам\'ять', '32 GB DDR5'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 4070'],
            ['Накопичувач (SSD)', '1 TB NVMe M.2'],
            ['Миша', 'HyperX Pulsefire'],
            ['Клавіатура', 'Logitech G213'],
            ['Монітор', 'ASUS TUF Gaming 240 Hz'],
        ],
        'extra': [],
    },
    'vip': {
        'title': 'VIP',
        'tier': 'Преміум-зона',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 7 7800X3D'],
            ['Материнська плата', 'B650E'],
            ['Оперативна пам\'ять', '32 GB DDR5'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 4080 Super 16GB'],
            ['Накопичувач (SSD)', '2 TB NVMe M.2'],
            ['Миша', 'Logitech G Pro X Superlight'],
            ['Клавіатура', 'MCHOSE JET 75 HE'],
            ['Монітор', 'ASUS TUF Gaming 360 Hz'],
        ],
        'extra': [],
    },
    'stream': {
        'title': 'STREAM',
        'tier': 'Stream-Room',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 9 7900X'],
            ['Материнська плата', 'Z790'],
            ['Оперативна пам\'ять', '64 GB DDR5'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 4080 Super'],
            ['Накопичувач (SSD)', '2 TB NVMe M.2'],
            ['Клавіатура', 'MCHOSE JET 75 HE'],
            ['Монітор', 'ASUS TUF Gaming 360 Hz'],
        ],
        'extra': [
            ['Мониторы', 'Основний 27" QHD (360 Hz) + допоміжний 24" FHD (60–144 Hz)'],
            ['Аудіо', 'Студійний мікрофон Fifine AM8'],
            ['Відео', 'Веб-камера 4K'],
            ['Світло та кріплення', 'Пантограф для мікрофона, LED-софтбокси'],
        ],
    },
}


PC_SPECS = {
    'default': {
        'title': 'DEFAULT',
        'tier': 'Базова зона',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 5 5600'],
            ['Материнська плата', 'B550 / B660'],
            ['Оперативна пам\'ять', '16 GB DDR4 (3200–3600 MHz)'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 3060 12GB'],
            ['Накопичувач (SSD)', '512 GB NVMe M.2'],
            ['Миша', 'HyperX Pulsefire'],
            ['Клавіатура', 'Logitech G213'],
            ['Монітор', 'ASUS TUF Gaming 144 Hz'],
        ],
        'extra': [],
    },
    'pro': {
        'title': 'PRO',
        'tier': 'Для змагальних матчів',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 7 5700X3D'],
            ['Материнська плата', 'B650 / B760'],
            ['Оперативна пам\'ять', '32 GB DDR5'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 4070'],
            ['Накопичувач (SSD)', '1 TB NVMe M.2'],
            ['Миша', 'HyperX Pulsefire'],
            ['Клавіатура', 'Logitech G213'],
            ['Монітор', 'ASUS TUF Gaming 240 Hz'],
        ],
        'extra': [],
    },
    'vip': {
        'title': 'VIP',
        'tier': 'Преміум-зона',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 7 7800X3D'],
            ['Материнська плата', 'B650E'],
            ['Оперативна пам\'ять', '32 GB DDR5'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 4080 Super 16GB'],
            ['Накопичувач (SSD)', '2 TB NVMe M.2'],
            ['Миша', 'Logitech G Pro X Superlight'],
            ['Клавіатура', 'MCHOSE JET 75 HE'],
            ['Монітор', 'ASUS TUF Gaming 360 Hz'],
        ],
        'extra': [],
    },
    'stream': {
        'title': 'STREAM',
        'tier': 'Stream-Room',
        'parts': [
            ['Процесор (CPU)', 'AMD Ryzen 9 7900X'],
            ['Материнська плата', 'Z790'],
            ['Оперативна пам\'ять', '64 GB DDR5'],
            ['Відеокарта (GPU)', 'NVIDIA GeForce RTX 4080 Super'],
            ['Накопичувач (SSD)', '2 TB NVMe M.2'],
            ['Клавіатура', 'MCHOSE JET 75 HE'],
            ['Монітор', 'ASUS TUF Gaming 360 Hz'],
        ],
        'extra': [
            ['Монітори', 'Основний 27" QHD (360 Hz) + допоміжний 24" FHD (60–144 Hz)'],
            ['Аудіо', 'Студійний мікрофон Fifine AM8'],
            ['Відео', 'Веб-камера 4K'],
            ['Світло та кріплення', 'Пантограф для мікрофона, LED-софтбокси'],
        ],
    },
}

def get_pc_kind(name):
    name = name.lower()

    if name.endswith('stream'):
        return 'stream'
    if name.endswith('vip'):
        return 'vip'
    if name.endswith('pro'):
        return 'pro'
    if name.endswith('defolt') or name.endswith('default'):
        return 'default'

    return ''

<<<<<<< HEAD
@user_passes_test(is_admin_or_staff)
=======
@staff_member_required
>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
def admin_computers(request):
    if request.method == 'POST':
        computer = get_object_or_404(
            Computer,
            pk=request.POST.get('computer_id')
        )
        new_status = request.POST.get('status')

        if new_status in ('available', 'occupied', 'maintenance'):
            Computer.objects.filter(pk=computer.pk).update(
                status=new_status,
                manual_occupied=(new_status == 'occupied'),
            )

        return redirect('admin_computers')

    update_computer_statuses()

    computers = list(Computer.objects.order_by('name'))

    for pc in computers:
        pc.kind = get_pc_kind(pc.name)

    return render(request, 'club/admin_computers.html', {
        'computers': computers,
        'specs': PC_SPECS,
    })



<<<<<<< HEAD
@user_passes_test(is_admin_or_staff)
@require_POST
def admin_booking_action(request, booking_id):
=======
@login_required
@require_POST
def admin_booking_action(request, booking_id):
    if request.user.username != 'admin' or not request.user.is_staff:
        return HttpResponseForbidden('Доступ заборонено.')

>>>>>>> 9015b66f1985c13d9b71b39eddfabeba065ab1a1
    booking = get_object_or_404(Booking, id=booking_id)
    action = request.POST.get('action')

    if action == 'toggle_payment':
        if booking.payment_status == 'paid':
            booking.payment_status = 'unpaid'
        else:
            booking.payment_status = 'paid'

        booking.save(update_fields=['payment_status'])

    elif action == 'delete':
        booking.delete()
        update_computer_statuses()

    return redirect('admin_bookings')
