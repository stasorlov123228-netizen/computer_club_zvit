from urllib.parse import urlencode

from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ..models import Booking

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

    if booking_record.user_id and booking_record.user_id != request.user.id:
        raise Http404
    if booking_record.payment_method != 'card':
        return redirect('my_bookings' if booking_record.user_id else 'home')

    if request.method == 'POST':
        if request.POST.get('demo_confirm') != '1':
            return render(request, 'club/payment_result.html', {
                'booking': booking_record,
                'payment_pending': True,
                'payment_error': (
                    'Не вдалося підтвердити оплату. '
                    'Перевірте дані та спробуйте ще раз.'
                ),
            }, status=400)
        if (
            booking_record.status == 'cancelled'
            or booking_record.start_time <= timezone.now()
        ):
            return render(request, 'club/payment_result.html', {
                'booking': booking_record,
                'payment_pending': False,
                'payment_error': (
                    'Оплату неможливо підтвердити: бронювання скасоване '
                    'або час його початку вже минув.'
                ),
            }, status=400)
        booking_record.status = 'confirmed'
        booking_record.payment_status = 'paid'
        booking_record.save(update_fields=['status', 'payment_status'])
        success_url = reverse(
            'payment_result',
            kwargs={'booking_id': booking_record.pk},
        )
        query = {'demo_success': '1'}
        if access_token:
            query['access'] = access_token
        return redirect(f'{success_url}?{urlencode(query)}')

    if (
        request.GET.get('demo_success') == '1'
        and booking_record.status == 'confirmed'
        and booking_record.payment_status == 'paid'
    ):
        return render(request, 'club/booking_success.html', {
            'booking': booking_record,
            'demo_payment': True,
        })

    if booking_record.payment_status == 'paid':
        if booking_record.user_id:
            return redirect('my_bookings')
        return render(request, 'club/booking_success.html', {
            'booking': booking_record,
        })

    return render(request, 'club/payment_result.html', {
        'booking': booking_record,
        'payment_pending': booking_record.payment_status != 'paid',
    })
