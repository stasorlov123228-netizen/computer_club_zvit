
from decimal import Decimal, InvalidOperation

from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def format_currency(amount):
    """Форматує ціну в гривнях і безпечно обробляє порожні значення."""
    if amount is None or amount == '':
        return '-'

    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return '-'

    return f'{value:.2f} грн'


@register.simple_tag
def booking_status_badge(status):
    """Повертає HTML-позначку зі статусом бронювання."""
    badges = {
        'pending': ('bg-warning text-dark', 'Очікує оплати'),
        'confirmed': ('bg-success text-white', 'Підтверджено'),
        'cancelled': ('bg-danger text-white', 'Скасовано'),
    }

    missing_label = 'Не вказано'

    css_class, label = badges.get(
        status,
        ('bg-secondary text-white', status or missing_label),
    )

    return format_html(
        '<span class="badge {}">{}</span>',
        css_class,
        label,
    )


@register.inclusion_tag('club/includes/tariff_card.html')
def render_tariff_card(tariff):
    """Відображає картку тарифу."""
    return {'tariff': tariff}


@register.inclusion_tag('club/includes/computer_card.html')
def render_computer_card(computer):
    """Відображає картку комп'ютера."""
    return {'computer': computer}
