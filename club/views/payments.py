from urllib.parse import urlencode

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..forms import CardPaymentForm
from ..models import Booking, Payment
from ..services import booking_pricing, synchronize_payment_record


def payment_page_context(booking, form=None):
    context = {
        'booking': booking,
        'payment_pending': booking.payment_status != 'paid',
        'payment_form': form or CardPaymentForm(),
        'pricing_available': False,
    }
    try:
        duration_hours, total_amount = booking_pricing(booking)
    except ValidationError as error:
        context['payment_error'] = error.messages[0]
        context['payment_pending'] = False
    else:
        context.update({
            'price_per_hour': booking.tariff.price_per_hour,
            'duration_hours': format(duration_hours.normalize(), 'f'),
            'total_amount': total_amount,
            'pricing_available': True,
        })
    return context


def payment_confirmation_context(booking):
    duration_hours, calculated_amount = booking_pricing(booking)
    payment = Payment.objects.filter(booking=booking).first()
    if (
        payment is None
        or not payment.is_paid
        or payment.status != 'paid'
    ):
        return None

    return {
        'booking': booking,
        'card_payment_confirmed': True,
        'price_per_hour': booking.tariff.price_per_hour,
        'duration_hours': format(duration_hours.normalize(), 'f'),
        'total_amount': (
            payment.amount
            if payment.amount is not None
            else calculated_amount
        ),
    }


@require_http_methods(['GET', 'POST'])
def payment_result(request, booking_id):
    access_token = ''
    if request.user.is_authenticated:
        booking_record = get_object_or_404(
            Booking,
            pk=booking_id,
            user=request.user,
        )
    else:
        access_token = request.GET.get('access', '')
        try:
            token_booking_id = signing.loads(
                access_token,
                salt='club.guest-booking',
            )
        except signing.BadSignature as error:
            raise Http404 from error
        if token_booking_id != booking_id:
            raise Http404
        booking_record = get_object_or_404(
            Booking,
            pk=booking_id,
            user__isnull=True,
        )

    if booking_record.payment_method != 'card':
        return redirect('club:my_bookings' if booking_record.user_id else 'club:home')

    success_url = reverse(
        'club:payment_result',
        kwargs={'booking_id': booking_record.pk},
    )
    success_query = {'payment_success': '1'}
    if access_token:
        success_query['access'] = access_token
    success_url = f'{success_url}?{urlencode(success_query)}'

    if request.method == 'POST':
        if booking_record.payment_status == 'paid':
            return redirect(success_url)

        form = CardPaymentForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                'club/payment_result.html',
                payment_page_context(booking_record, form),
                status=400,
            )

        payment_error = ''
        with transaction.atomic():
            locked_booking = get_object_or_404(
                Booking.objects.select_for_update().select_related('tariff'),
                pk=booking_id,
            )
            if request.user.is_authenticated:
                if locked_booking.user_id != request.user.pk:
                    raise Http404
            elif locked_booking.user_id is not None:
                raise Http404

            if locked_booking.payment_status == 'paid':
                pass
            elif locked_booking.payment_method != 'card':
                raise Http404
            elif (
                locked_booking.status == 'cancelled'
                or locked_booking.start_time <= timezone.now()
            ):
                payment_error = (
                    'Оплату неможливо підтвердити: бронювання скасоване '
                    'або час його початку вже минув.'
                )
            else:
                try:
                    booking_pricing(locked_booking)
                except ValidationError as error:
                    payment_error = error.messages[0]
                else:
                    try:
                        with transaction.atomic():
                            locked_booking.status = 'confirmed'
                            locked_booking.payment_status = 'paid'
                            locked_booking.save(
                                update_fields=['status', 'payment_status'],
                            )
                            synchronize_payment_record(locked_booking)
                    except ValidationError as error:
                        payment_error = error.messages[0]

        if payment_error:
            return render(
                request,
                'club/payment_result.html',
                {
                    **payment_page_context(booking_record),
                    'payment_pending': False,
                    'payment_error': payment_error,
                },
                status=400,
            )

        return redirect(success_url)

    if booking_record.payment_status == 'paid':
        if booking_record.status == 'confirmed':
            try:
                confirmation = payment_confirmation_context(booking_record)
            except ValidationError:
                confirmation = None
            if confirmation:
                return render(
                    request,
                    'club/booking_success.html',
                    confirmation,
                )

        return render(
            request,
            'club/payment_result.html',
            {
                **payment_page_context(booking_record),
                'payment_pending': False,
                'payment_error': (
                    'Не вдалося підтвердити бронювання за записом платежу. '
                    'Зверніться до адміністратора клубу.'
                ),
            },
            status=409,
        )

    return render(
        request,
        'club/payment_result.html',
        payment_page_context(booking_record),
    )
