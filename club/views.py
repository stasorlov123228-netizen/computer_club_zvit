
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Computer, Tariff, Booking, Payment



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
    return render(request, 'club/account.html')





@login_required
def my_bookings(request):
    update_computer_statuses()

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

    errors = []
    name = request.POST.get('name', '').strip()
    tariff_code = request.POST.get('tariff', '').strip()
    duration_value = request.POST.get('duration', '').strip()
    date_value = request.POST.get('date', '').strip()
    time_value = request.POST.get('time', '').strip()
    payment_method = request.POST.get('payment_method', '').strip()
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

            if not computer:
                errors.append(
                    'Немає вільного комп’ютера для цього тарифу '
                    'на вибраний час.'
                )

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

    



def login_view(request):
    if request.user.is_authenticated:
        if request.user.username == 'admin':
            return redirect('admin_panel')
        return redirect('home')

    form = AuthenticationForm(
        request,
        data=request.POST or None
    )

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)

        if user.username == 'admin':
            return redirect('admin_panel')

        return redirect('home')

    return render(request, 'club/login.html', {'form': form})


class CustomUserCreationForm(forms.ModelForm):
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

        return user


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = CustomUserCreationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('home')

    return render(request, 'club/register.html', {'form': form})


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

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()

        if phone:
            sent = True
        else:
            error = 'Будь ласка, введіть номер телефону.'

    return render(request, 'club/section_page.html', {
        'page_type': 'partnership',
        'title': 'Партнерство',
        'sent': sent,
        'error': error,
    })



def payment_result(request, booking_id):
    update_computer_statuses()

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



def liqpay_callback(request):
    return redirect('payment_result')

@login_required
def admin_panel(request):
    if request.user.username != 'admin' or not request.user.is_staff:
        return redirect('home')

    return render(request, 'club/admin_panel.html')


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
    if request.user.username != 'admin' or not request.user.is_staff:
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

@staff_member_required
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



@login_required
@require_POST
def admin_booking_action(request, booking_id):
    if request.user.username != 'admin' or not request.user.is_staff:
        return HttpResponseForbidden('Доступ заборонено.')

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
