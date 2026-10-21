from decimal import Decimal

from django.test import SimpleTestCase

from .templatetags.club_tags import (
    booking_status_badge, format_currency, render_computer_card,
    render_tariff_card,
)


class ClubTemplateTagTests(SimpleTestCase):
    def test_currency_formatting_and_empty_values(self):
        self.assertEqual(format_currency(Decimal('125.5')), '125.50 \u0433\u0440\u043d')
        self.assertEqual(format_currency(None), '\u2014')
        self.assertEqual(format_currency(''), '\u2014')
        self.assertEqual(format_currency('not-a-price'), '\u2014')

    def test_booking_badge_handles_known_empty_and_untrusted_status(self):
        self.assertIn('\u041f\u0456\u0434\u0442\u0432\u0435\u0440\u0434\u0436\u0435\u043d\u043e', booking_status_badge('confirmed'))
        self.assertIn('\u041d\u0435 \u0432\u043a\u0430\u0437\u0430\u043d\u043e', booking_status_badge(None))
        badge = booking_status_badge('<script>alert(1)</script>')
        self.assertNotIn('<script>', badge)
        self.assertIn('&lt;script&gt;', badge)

    def test_inclusion_tags_return_the_context_used_by_real_card_templates(self):
        computer = object()
        tariff = object()
        self.assertEqual(render_computer_card(computer), {'computer': computer})
        self.assertEqual(render_tariff_card(tariff), {'tariff': tariff})
