"""Public view imports retained for URLconf and legacy imports."""

from ..forms import (
    AdminBookingEditForm, BookingEditForm, BookingModelForm,
    CustomUserCreationForm, EmailForm, PhoneNumberForm, clean_phone_fields,
)
from ..services import (
    BOOKING_DURATION_CHOICES, PC_SPECS, admin_booking_initial,
    admin_booking_queryset, booking_duration_choices, booking_duration_value,
    duration_as_timedelta, find_available_computer, get_pc_kind,
    get_tariff_kind, is_admin_or_staff, lock_booking_payment_method,
    update_computer_statuses,
)
from .admin import (
    admin_booking_action, admin_bookings, admin_computers, admin_panel,
    admin_tariffs, admin_update_tariff_price, admin_users,
    edit_admin_booking, render_admin_bookings_with_error,
)
from .auth import login_view, logout_view, register_view
from .bookings import (
    BookingCreateView, BookingDeleteView, BookingDetailView,
    BookingListView, BookingUpdateView, account_view,
    booking, cancel_my_booking, edit_my_booking, home, my_bookings,
    render_my_bookings,
)
from .pages import (
    clubs_view, feedback_view, news_view, partnership_view,
    tournaments_view,
)
from .payments import payment_result

from .computers import ComputerDetailView, ComputerListView
from .tariffs import TariffDetailView, TariffListView
