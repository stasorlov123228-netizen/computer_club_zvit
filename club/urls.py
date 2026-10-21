
from django.urls import path
from . import views

urlpatterns = [
    path('bookings/', views.BookingListView.as_view(), name='booking_list'),
    path('bookings/new/', views.BookingCreateView.as_view(), name='booking_create'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/<int:pk>/edit/', views.BookingUpdateView.as_view(), name='booking_update'),
    path('bookings/<int:pk>/delete/', views.BookingDeleteView.as_view(), name='booking_delete'),
    path('computers/', views.ComputerListView.as_view(), name='computer_list'),
    path('computers/<int:pk>/', views.ComputerDetailView.as_view(), name='computer_detail'),
    path('tariffs/', views.TariffListView.as_view(), name='tariff_list'),
    path('tariffs/<int:pk>/', views.TariffDetailView.as_view(), name='tariff_detail'),
    path('', views.home, name='home'),
    path('booking/', views.booking, name='booking'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('account/', views.account_view, name='account'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path(
        'my-bookings/<int:booking_id>/edit/',
        views.edit_my_booking,
        name='edit_my_booking',
    ),
    path(
        'my-bookings/<int:booking_id>/cancel/',
        views.cancel_my_booking,
        name='cancel_my_booking',
    ),

    path('tournaments/', views.tournaments_view, name='tournaments'),
    path('news/', views.news_view, name='news'),
    path('clubs/', views.clubs_view, name='clubs'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('partnership/', views.partnership_view, name='partnership'),

    path(
        'payment/<int:booking_id>/',
        views.payment_result,
        name='payment_result'
    ),

    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/bookings/', views.admin_bookings, name='admin_bookings'),
    path(
        'admin-panel/bookings/<int:booking_id>/edit/',
        views.edit_admin_booking,
        name='edit_admin_booking',
    ),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/tariffs/', views.admin_tariffs, name='admin_tariffs'),
    path('admin-panel/computers/', views.admin_computers, name='admin_computers'),

    path(
    'admin-panel/bookings/<int:booking_id>/action/',
    views.admin_booking_action,
    name='admin_booking_action'
),


path(
    'admin-panel/tariffs/<int:tariff_id>/price/',
    views.admin_update_tariff_price,
    name='admin_update_tariff_price'
),

]
