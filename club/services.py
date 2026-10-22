from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Booking, Computer, Payment, Tariff

def booking_pricing(booking):
    """Return exact booked hours and the rounded currency amount."""
    if not booking.start_time or not booking.end_time or booking.end_time <= booking.start_time:
        raise ValidationError('Неможливо визначити вартість: перевірте час бронювання.')
    if not booking.tariff_id:
        raise ValidationError('Для бронювання не вибрано тариф.')

    tariff = booking.tariff
    price_per_hour = tariff.price_per_hour
    if price_per_hour is None:
        raise ValidationError('Для вибраного тарифу не вказано ціну за годину.')

    duration = booking.end_time - booking.start_time
    duration_seconds = (
        Decimal(duration.days) * Decimal('86400')
        + Decimal(duration.seconds)
        + Decimal(duration.microseconds) / Decimal('1000000')
    )
    duration_hours = duration_seconds / Decimal('3600')
    total_amount = (price_per_hour * duration_hours).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP,
    )
    return duration_hours, total_amount


def synchronize_payment_record(booking):
    """Keep the one-to-one payment row aligned with its booking state."""
    if not booking.pk:
        raise ValueError('Save the booking before synchronizing its payment.')

    with transaction.atomic():
        locked_booking = Booking.objects.select_for_update().select_related(
            'tariff',
        ).get(pk=booking.pk)
        _, amount = booking_pricing(locked_booking)
        payment = Payment.objects.select_for_update().filter(
            booking=locked_booking,
        ).first()
        is_paid = locked_booking.payment_status == 'paid'

        if (
            is_paid
            and payment
            and payment.is_paid
            and payment.status == 'paid'
            and payment.amount != amount
        ):
            raise ValidationError(
                'The recorded payment amount does not match the booking.'
            )

        paid_at = None
        if is_paid:
            paid_at = (
                payment.paid_at
                if payment and payment.is_paid and payment.status == 'paid'
                else timezone.now()
            )

        values = {
            'amount': amount,
            'paid_at': paid_at,
            'is_paid': is_paid,
            'status': 'paid' if is_paid else 'unpaid',
        }
        if payment is None:
            return Payment.objects.create(
                booking=locked_booking,
                **values,
            )

        changed_fields = []
        for field, value in values.items():
            if getattr(payment, field) != value:
                setattr(payment, field, value)
                changed_fields.append(field)
        if changed_fields:
            payment.save(update_fields=changed_fields)
        return payment


def lock_booking_slot(computer, start, end, exclude_booking_id=None):
    """Lock a computer and recheck its booking interval before saving."""
    locked_computer = Computer.objects.select_for_update().get(pk=computer.pk)
    if locked_computer.status == 'maintenance' or locked_computer.manual_occupied:
        raise ValidationError('Цей комп’ютер зараз недоступний.')

    conflicts = Booking.objects.filter(
        computer=locked_computer,
        start_time__lt=end,
        end_time__gt=start,
    ).exclude(status='cancelled')
    if exclude_booking_id is not None:
        conflicts = conflicts.exclude(pk=exclude_booking_id)
    if conflicts.exists():
        raise ValidationError('Комп’ютер уже заброньований на цей час.')
    return locked_computer


BOOKING_DURATION_CHOICES = (
    ('1', '1 година'),
    ('2', '2 години'),
    ('3', '3 години'),
    ('5', '5 годин'),
    ('8', '8 годин'),
)

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

def booking_duration_value(booking):
    duration = booking.end_time - booking.start_time
    duration_seconds = (
        Decimal(duration.days) * Decimal('86400')
        + Decimal(duration.seconds)
        + Decimal(duration.microseconds) / Decimal('1000000')
    )
    duration_hours = duration_seconds / Decimal('3600')
    return format(duration_hours.normalize(), 'f')

def duration_as_timedelta(duration_hours):
    seconds = int(Decimal(str(duration_hours)) * Decimal('3600'))
    return timedelta(seconds=seconds)

def booking_duration_choices(booking=None):
    choices = list(BOOKING_DURATION_CHOICES)
    if booking:
        value = booking_duration_value(booking)
        if value not in {choice[0] for choice in choices}:
            choices.append((value, f'{value} год (поточна тривалість)'))
    return choices

def is_admin_or_staff(user):
    return user.is_authenticated and user.is_active and user.is_staff

def admin_booking_queryset(search_query=''):
    bookings = Booking.objects.select_related(
        'computer', 'tariff', 'user'
    ).order_by('-created_at')
    if search_query:
        bookings = bookings.filter(
            Q(customer_name__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(phone__icontains=search_query)
        )
    return bookings

def admin_booking_initial(booking_record):
    return {
        'computer': booking_record.computer_id,
        'tariff': booking_record.tariff_id,
        'start_time': booking_record.start_time,
        'duration': booking_duration_value(booking_record),
        'payment_method': booking_record.payment_method,
        'payment_status': booking_record.payment_status,
        'status': booking_record.status,
    }

def get_tariff_kind(name):
    return {
        'default': 'default',
        'standart': 'default',
        'standard': 'default',
        'pro': 'pro',
        'vip': 'vip',
        'stream': 'stream',
    }.get(name.strip().lower())

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
