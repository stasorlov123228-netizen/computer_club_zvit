from decimal import Decimal
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def format_currency(amount):
    """Форматує ціну у гривнях: 120.00 грн."""
    try:
        val = Decimal(str(amount))
        return f'{val:.2f} грн'
    except (ValueError, TypeError):
        return f'{amount} грн'


@register.simple_tag
def booking_status_badge(status):
    """Повертає HTML-бейдж зі статусом бронювання."""
    badges = {
        'pending': ('bg-warning text-dark', 'Очікує оплати'),
        'confirmed': ('bg-success text-white', 'Підтверджено'),
        'cancelled': ('bg-danger text-white', 'Скасовано'),
    }
    css_class, label = badges.get(status, ('bg-secondary text-white', status))
    return mark_safe(f'<span class="badge {css_class}">{label}</span>')


@register.inclusion_tag('club/includes/tariff_card.html')
def render_tariff_card(tariff):
    """Відображає картку тарифу."""
    return {'tariff': tariff}


@register.inclusion_tag('club/includes/computer_card.html')
def render_computer_card(computer):
    """Відображає картку комп\'ютера."""
    return {'computer': computer}

