from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import (
    AdminBookingEditForm, BookingEditForm, BookingModelForm, EmailForm,
    PhoneNumberForm,
)
from ..models import Booking, Computer, Tariff, UserProfile
from ..phone_numbers import PHONE_COUNTRIES, split_phone_number, validate_phone_number
from ..services import (
    booking_duration_value, duration_as_timedelta,
    find_available_computer, lock_booking_payment_method,
    update_computer_statuses,
)

class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'club/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 5

    def get_queryset(self):
        queryset = Booking.objects.select_related(
            'user', 'computer', 'tariff',
        ).order_by('-created_at', '-pk')
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(user=self.request.user)
        status = self.request.GET.get('status')
        search = self.request.GET.get('search', '').strip()
        if status:
            queryset = queryset.filter(status=status)
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(computer__name__icontains=search)
                | Q(tariff__name__icontains=search)
            )
        return queryset

class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = 'club/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'user', 'computer', 'tariff',
        )
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(user=self.request.user)
        return queryset

class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingModelForm
    template_name = 'club/booking_form.html'

    def get_initial(self):
        initial = super().get_initial()
        for field in ('computer', 'tariff'):
            value = self.request.GET.get(field)
            if value and value.isdigit():
                initial[field] = value
        profile = UserProfile.objects.filter(user=self.request.user).first()
        if profile:
            initial.setdefault('phone', profile.phone)
        initial.setdefault('customer_name', self.request.user.get_full_name()
                           or self.request.user.username)
        return initial

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class BookingUpdateView(LoginRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingModelForm
    template_name = 'club/booking_form.html'
    context_object_name = 'booking'

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(user=self.request.user)
        return queryset

class BookingDeleteView(LoginRequiredMixin, DeleteView):
    model = Booking
    template_name = 'club/booking_confirm_delete.html'
    success_url = reverse_lazy('booking_list')

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(user=self.request.user)
        return queryset

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
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    _, country_code, local_number = split_phone_number(profile.phone)
    email_form = EmailForm(initial={'email': request.user.email})
    phone_form = PhoneNumberForm(initial={
        'phone_country': country_code,
        'phone_local': local_number,
    })

    if request.method == 'POST':
        if 'update_email' in request.POST:
            email_form = EmailForm(request.POST)
            if email_form.is_valid():
                request.user.email = email_form.cleaned_data['email']
                request.user.save(update_fields=['email'])
                return redirect('account')
        elif 'update_phone' in request.POST:
            phone_form = PhoneNumberForm(request.POST)
            if phone_form.is_valid():
                profile.phone = phone_form.cleaned_data['phone']
                profile.save(update_fields=['phone'])
                return redirect('account')

    return render(request, 'club/account.html', {
        'email_form': email_form,
        'phone_form': phone_form,
    })

@login_required
def my_bookings(request):
    update_computer_statuses()

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
        if (
            booking_record.status != 'cancelled'
            and booking_record.start_time > now
        ):
            if booking_record.id == editing_booking_id and edit_form is not None:
                form = edit_form
            else:
                form = BookingEditForm(
                    booking=booking_record,
                    initial={
                        'start_time': booking_record.start_time,
                        'duration': booking_duration_value(booking_record),
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
        'now': now,
    })

@login_required
@require_POST
def cancel_my_booking(request, booking_id):
    with transaction.atomic():
        booking_record = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
            user=request.user,
        )
        if booking_record.status == 'cancelled':
            messages.error(request, 'Це бронювання вже скасоване.')
        elif booking_record.start_time <= timezone.now():
            messages.error(
                request,
                'Скасувати бронювання можна лише до початку сеансу.',
            )
        elif booking_record.payment_method == 'card':
            messages.error(
                request,
                'Бронювання з оплатою карткою скасувати неможливо.',
            )
        else:
            booking_record.status = 'cancelled'
            booking_record.save(update_fields=['status'])
            messages.success(request, 'Бронювання успішно скасоване.')

    update_computer_statuses()
    return redirect('my_bookings')

@login_required
@require_POST
def edit_my_booking(request, booking_id):
    booking_record = get_object_or_404(
        Booking,
        pk=booking_id,
        user=request.user,
    )
    form = BookingEditForm(request.POST, booking=booking_record)
    if booking_record.payment_status == 'paid':
        lock_booking_payment_method(form, booking_record)
        if not form.is_valid():
            return render_my_bookings(request, booking_id, form)
        form.add_error(
            None,
            'Оплачене бронювання не можна редагувати. '
            'Зверніться до адміністратора клубу.',
        )
        return render_my_bookings(request, booking_id, form)

    if not form.is_valid():
        return render_my_bookings(request, booking_id, form)
    needs_payment = False
    with transaction.atomic():
        booking_record = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
            user=request.user,
        )
        if booking_record.payment_status == 'paid':
            form.add_error(
                None,
                'Оплачене бронювання не можна редагувати. '
                'Зверніться до адміністратора клубу.',
            )
        elif (
            booking_record.status == 'cancelled'
            or booking_record.start_time <= timezone.now()
        ):
            form.add_error(
                None,
                'Це бронювання вже не можна редагувати.',
            )
        else:
            start = form.cleaned_data['start_time']
            end = start + duration_as_timedelta(
                form.cleaned_data['duration']
            )
            tariff = form.cleaned_data['tariff']
            if start <= timezone.now():
                form.add_error(
                    'start_time',
                    'Оберіть час початку в майбутньому.',
                )
            else:
                tariff_codes = {
                    'DEFAULT': 'default',
                    'STANDART': 'default',
                    'STANDARD': 'default',
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
                        booking_record.status = (
                            'pending'
                            if booking_record.payment_method == 'card'
                            else 'confirmed'
                        )
                    booking_record.save(update_fields=[
                        'start_time',
                        'end_time',
                        'payment_method',
                        'tariff',
                        'computer',
                        'status',
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
    phone_required = not request.user.is_authenticated or not phone
    phone_local = (
        request.POST.get('phone_local', '').strip()
        if request.method == 'POST' and phone_required
        else saved_local_number
    )
    context = {
        'errors': [],
        'phone_countries': [list(country) for country in PHONE_COUNTRIES],
        'phone_country': phone_country,
        'phone_iso': iso,
        'phone_local': phone_local,
        'phone_required': phone_required,
        'missing_profile_phone': request.user.is_authenticated and not phone,
    }

    if request.method != 'POST':
        return render(request, 'club/booking.html', context)

    errors = []
    name = (
        request.user.username
        if request.user.is_authenticated
        else request.POST.get('name', '').strip()
    )
    tariff_code = request.POST.get('tariff', '').strip()
    duration_value = request.POST.get('duration', '').strip()
    date_value = request.POST.get('date', '').strip()
    time_value = request.POST.get('time', '').strip()
    payment_method = request.POST.get('payment_method', '').strip()

    if phone_required:
        phone_country = request.POST.get('phone_country', '').strip()
        phone_local = request.POST.get('phone_local', '').strip()
        try:
            phone = validate_phone_number(phone_country, phone_local)
        except ValidationError as error:
            errors.extend(error.messages)

    if not request.user.is_authenticated and not name:
        errors.append("Введіть ім’я.")

    tariff_names = {
        'default': ('DEFAULT', 'STANDART', 'STANDARD'),
        'pro': ('PRO',),
        'vip': ('VIP',),
        'stream': ('STREAM',),
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
        for tariff_name in tariff_names[tariff_code]:
            tariff = Tariff.objects.filter(
                name__iexact=tariff_name
            ).first()
            if tariff:
                break
        if not tariff:
            errors.append('Цей тариф ще не доданий в адмінпанелі.')

    if not errors:
        with transaction.atomic():
            computer = find_available_computer(
                tariff_code,
                start,
                end,
            )
            if not computer:
                errors.append(
                    'Немає вільного комп’ютера для цього тарифу '
                    'на вибраний час.'
                )
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
                    status='pending' if payment_method == 'card' else 'confirmed',
                )
                if request.user.is_authenticated and phone_required:
                    UserProfile.objects.update_or_create(
                        user=request.user,
                        defaults={'phone': phone},
                    )

    if booking_record:
        if payment_method == 'card':
            payment_url = reverse(
                'payment_result',
                kwargs={'booking_id': booking_record.id},
            )
            if not request.user.is_authenticated:
                access_token = signing.dumps(
                    booking_record.pk,
                    salt='club.guest-booking',
                )
                payment_url = f'{payment_url}?{urlencode({"access": access_token})}'
            return redirect(
                payment_url,
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
