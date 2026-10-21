from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from ..forms import AdminBookingEditForm
from ..models import Booking, Computer, Tariff
from ..services import (
    PC_SPECS, admin_booking_initial, admin_booking_queryset,
    booking_duration_value, duration_as_timedelta, get_pc_kind,
    get_tariff_kind, is_admin_or_staff, update_computer_statuses,
)

@login_required
def admin_panel(request):
    if not is_admin_or_staff(request.user):
        return redirect('home')

    return render(request, 'club/admin_panel.html')

@user_passes_test(is_admin_or_staff)
def admin_bookings(request):
    search_query = request.GET.get('q', '').strip()
    bookings = list(admin_booking_queryset(search_query))
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
        'search_query': search_query,
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
        end = start + duration_as_timedelta(
            form.cleaned_data['duration']
        )
        status = form.cleaned_data['status']
        computer = Computer.objects.select_for_update().get(pk=computer.pk)

        if (
            booking_record.payment_status == 'paid'
            and (
                start != booking_record.start_time
                or (
                    form.cleaned_data['duration']
                    != booking_duration_value(booking_record)
                )
                or tariff.pk != booking_record.tariff_id
            )
        ):
            form.add_error(
                None,
                'Параметри оплаченого бронювання змінювати не можна.',
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
                if (
                    booking_record.payment_method == 'card'
                    and booking_record.payment_status != 'paid'
                    and booking_record.status != 'cancelled'
                ):
                    booking_record.status = 'pending'
                elif (
                    booking_record.payment_method == 'cash'
                    and booking_record.status == 'pending'
                ):
                    booking_record.status = 'confirmed'
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
    search_query = request.POST.get('q', '').strip()
    bookings = list(admin_booking_queryset(search_query))
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
        'search_query': search_query,
    })

@user_passes_test(is_admin_or_staff)
@require_http_methods(['GET', 'POST'])
def admin_users(request):
    if request.method == 'POST':
        user_to_delete = get_object_or_404(
            User,
            pk=request.POST.get('user_id'),
        )
        if user_to_delete.pk == request.user.pk:
            messages.error(request, 'Не можна видалити власний акаунт.')
        elif user_to_delete.is_superuser:
            messages.error(
                request,
                'Акаунт суперадміністратора видалити неможливо.',
            )
        else:
            username = user_to_delete.username
            user_to_delete.delete()
            messages.success(
                request,
                f'Акаунт «{username}» видалено.',
            )
        search_query = request.POST.get('q', '').strip()
        if search_query:
            return redirect(
                f'{reverse("admin_users")}?{urlencode({"q": search_query})}'
            )
        return redirect('admin_users')

    search_query = request.GET.get('q', '').strip()
    users = User.objects.select_related('profile').order_by('-date_joined')
    if search_query:
            users = users.filter(
                Q(username__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(profile__phone__icontains=search_query)
            )

    return render(request, 'club/admin_users.html', {
            'users': users,
            'search_query': search_query,
    })

@user_passes_test(is_admin_or_staff)
def admin_tariffs(request):
    return render(request, 'club/admin_tariffs.html', {
        'tariffs': Tariff.objects.all(),
    })

@login_required
def admin_update_tariff_price(request, tariff_id):
    if not is_admin_or_staff(request.user):
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

@user_passes_test(is_admin_or_staff)
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

@user_passes_test(is_admin_or_staff)
@require_POST
def admin_booking_action(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    action = request.POST.get('action')

    if action == 'toggle_payment':
        booking.payment_status = (
            'unpaid' if booking.payment_status == 'paid' else 'paid'
        )
        if booking.payment_method == 'card' and booking.status != 'cancelled':
            booking.status = (
                'confirmed'
                if booking.payment_status == 'paid'
                else 'pending'
            )
            booking.save(update_fields=['payment_status', 'status'])
        else:
            booking.save(update_fields=['payment_status'])

    elif action == 'delete':
        booking.delete()
        update_computer_statuses()

    return redirect('admin_bookings')
