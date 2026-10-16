
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('booking/', views.booking, name='booking'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('account/', views.account_view, name='account'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),

    path('tournaments/', views.tournaments_view, name='tournaments'),
    path('news/', views.news_view, name='news'),
    path('clubs/', views.clubs_view, name='clubs'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('partnership/', views.partnership_view, name='partnership'),

    path(
        'payment/liqpay/callback/',
        views.liqpay_callback,
        name='liqpay_callback'
    ),
    path(
        'payment/<int:booking_id>/',
        views.payment_result,
        name='payment_result'
    ),

    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/bookings/', views.admin_bookings, name='admin_bookings'),
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

