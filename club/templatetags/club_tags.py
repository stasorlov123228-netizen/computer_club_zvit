from decimal import Decimal, InvalidOperation

from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def format_currency(amount):
    """Format a price in hryvnias and safely handle missing values."""
    if amount is None or amount == '':
        return '\u2014'
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        return '\u2014'
    return f'{value:.2f} \u0433\u0440\u043d'


@register.simple_tag
def booking_status_badge(status):
    """Return an HTML badge with an escaped status label."""
    badges = {
        'pending': ('bg-warning text-dark', '\u041e\u0447\u0456\u043a\u0443\u0454 \u043e\u043f\u043b\u0430\u0442\u0438'),
        'confirmed': ('bg-success text-white', '\u041f\u0456\u0434\u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u043e'),
        'cancelled': ('bg-danger text-white', '\u0421\u043a\u0430\u0441\u043e\u0432\u0430\u043d\u043e'),
    }
    missing_label = '\u041d\u0435 \u0432\u043a\u0430\u0437\u0430\u043d\u043e'
    css_class, label = badges.get(
        status, ('bg-secondary text-white', status or missing_label),
    )
    return format_html('<span class="badge {}">{}</span>', css_class, label)


@register.inclusion_tag('club/includes/tariff_card.html')
def render_tariff_card(tariff):
    return {'tariff': tariff}


@register.inclusion_tag('club/includes/computer_card.html')
def render_computer_card(computer):
    return {'computer': computer}
