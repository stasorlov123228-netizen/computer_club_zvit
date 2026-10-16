from django.core.exceptions import ValidationError


PHONE_COUNTRIES = (
    ('ua', 'Україна', '+380', 9, 9),
    ('us', 'США / Канада', '+1', 10, 10),
    ('gb', 'Велика Британія', '+44', 10, 10),
    ('pl', 'Польща', '+48', 9, 9),
    ('de', 'Німеччина', '+49', 10, 11),
    ('fr', 'Франція', '+33', 9, 9),
    ('it', 'Італія', '+39', 9, 10),
    ('es', 'Іспанія', '+34', 9, 9),
    ('cz', 'Чехія', '+420', 9, 9),
    ('sk', 'Словаччина', '+421', 9, 9),
    ('ro', 'Румунія', '+40', 9, 9),
    ('md', 'Молдова', '+373', 8, 8),
    ('at', 'Австрія', '+43', 10, 11),
    ('ch', 'Швейцарія', '+41', 9, 9),
    ('nl', 'Нідерланди', '+31', 9, 9),
    ('be', 'Бельгія', '+32', 8, 9),
    ('pt', 'Португалія', '+351', 9, 9),
    ('gr', 'Греція', '+30', 10, 10),
    ('bg', 'Болгарія', '+359', 8, 9),
    ('hr', 'Хорватія', '+385', 8, 9),
    ('si', 'Словенія', '+386', 8, 8),
    ('hu', 'Угорщина', '+36', 9, 9),
    ('lt', 'Литва', '+370', 8, 8),
    ('lv', 'Латвія', '+371', 8, 8),
    ('ee', 'Естонія', '+372', 7, 8),
    ('fi', 'Фінляндія', '+358', 9, 10),
    ('se', 'Швеція', '+46', 9, 9),
    ('no', 'Норвегія', '+47', 8, 8),
    ('dk', 'Данія', '+45', 8, 8),
    ('is', 'Ісландія', '+354', 7, 7),
    ('ie', 'Ірландія', '+353', 9, 9),
    ('tr', 'Туреччина', '+90', 10, 10),
    ('ge', 'Грузія', '+995', 9, 9),
    ('am', 'Вірменія', '+374', 8, 8),
    ('az', 'Азербайджан', '+994', 9, 9),
    ('kz', 'Казахстан / Росія', '+7', 10, 10),
    ('jp', 'Японія', '+81', 10, 10),
    ('kr', 'Південна Корея', '+82', 9, 10),
    ('cn', 'Китай', '+86', 11, 11),
    ('in', 'Індія', '+91', 10, 10),
    ('pk', 'Пакистан', '+92', 10, 10),
    ('bd', 'Бангладеш', '+880', 10, 10),
    ('th', 'Таїланд', '+66', 9, 9),
    ('vn', 'В’єтнам', '+84', 9, 10),
    ('my', 'Малайзія', '+60', 9, 10),
    ('sg', 'Сінгапур', '+65', 8, 8),
    ('id', 'Індонезія', '+62', 9, 11),
    ('ph', 'Філіппіни', '+63', 10, 10),
    ('il', 'Ізраїль', '+972', 9, 9),
    ('ae', 'ОАЕ', '+971', 9, 9),
    ('sa', 'Саудівська Аравія', '+966', 9, 9),
    ('eg', 'Єгипет', '+20', 10, 10),
    ('za', 'ПАР', '+27', 9, 9),
    ('ng', 'Нігерія', '+234', 10, 10),
    ('ke', 'Кенія', '+254', 9, 9),
    ('ma', 'Марокко', '+212', 9, 9),
    ('br', 'Бразилія', '+55', 10, 11),
    ('ar', 'Аргентина', '+54', 10, 10),
    ('cl', 'Чилі', '+56', 9, 9),
    ('co', 'Колумбія', '+57', 10, 10),
    ('mx', 'Мексика', '+52', 10, 10),
    ('au', 'Австралія', '+61', 9, 9),
    ('nz', 'Нова Зеландія', '+64', 8, 9),
)

PHONE_RULES = {
    dial_code: (min_length, max_length)
    for _, _, dial_code, min_length, max_length in PHONE_COUNTRIES
}

PHONE_COUNTRY_CHOICES = tuple(
    (dial_code, f'{name} ({dial_code})')
    for _, name, dial_code, _, _ in PHONE_COUNTRIES
)


def validate_phone_number(country_code, local_number):
    if country_code not in PHONE_RULES:
        raise ValidationError('Оберіть країну зі списку.')

    if not local_number:
        raise ValidationError('Введіть номер телефону.')

    if not local_number.isascii() or not local_number.isdigit():
        raise ValidationError('Номер телефону повинен містити лише цифри.')

    min_length, max_length = PHONE_RULES[country_code]
    if len(local_number) > max_length:
        raise ValidationError(
            f'Номер не може містити більше {max_length} цифр '
            'після коду країни.'
        )
    if not min_length <= len(local_number) <= max_length:
        expected = (
            str(min_length)
            if min_length == max_length
            else f'{min_length}–{max_length}'
        )
        raise ValidationError(
            f'Для {country_code} номер має містити {expected} цифр '
            'після коду країни.'
        )

    return f'{country_code}{local_number}'


def split_phone_number(phone):
    for _, _, dial_code, _, _ in sorted(
        PHONE_COUNTRIES,
        key=lambda country: len(country[2]),
        reverse=True,
    ):
        if phone.startswith(dial_code):
            country = next(
                item for item in PHONE_COUNTRIES if item[2] == dial_code
            )
            return country[0], dial_code, phone[len(dial_code):]

    return 'ua', '+380', ''
