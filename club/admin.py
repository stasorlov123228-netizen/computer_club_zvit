from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from .models import Computer, Tariff, Booking, Payment, UserProfile
from .views import update_computer_statuses


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 1
    max_num = 1
    can_delete = False
    verbose_name = 'Профіль користувача'
    verbose_name_plural = 'Контактні дані'
    fields = ('phone',)


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'phone', 'role', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'profile__phone')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')

    @admin.display(description='Телефон')
    def phone(self, obj):
        try:
            return obj.profile.phone or 'Не вказаний'
        except UserProfile.DoesNotExist:
            return 'Не вказаний'

    @admin.display(description='Роль')
    def role(self, obj):
        if obj.is_superuser:
            return 'Суперадміністратор'
        if obj.is_staff:
            return 'Адміністратор'
        return 'Клієнт'


@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status')
    list_filter = ('status',)
    search_fields = ('name',)

    def changelist_view(self, request, extra_context=None):
        update_computer_statuses()
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price_per_hour')
    search_fields = ('name',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer_name',
        'phone',
        'computer',
        'tariff',
        'start_time',
        'end_time',
        'duration',
    )

    list_filter = ('tariff', 'start_time')
    search_fields = (
        'customer_name',
        'phone',
        'user__username',
        'computer__name',
    )

    @admin.display(description='Тривалість')
    def duration(self, obj):
        difference = obj.end_time - obj.start_time
        total_minutes = int(difference.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if minutes:
            return f'{hours} год. {minutes} хв.'
        return f'{hours} год.'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'booking',
        'payment_status',
        'amount',
        'paid_at',
    )
    list_filter = ('booking__payment_status',)
    search_fields = (
        'booking__customer_name',
        'booking__phone',
        'booking__user__username',
        'booking__computer__name',
    )
    list_select_related = ('booking', 'booking__computer', 'booking__user')

    @admin.display(
        description='Статус оплати',
        ordering='booking__payment_status',
    )
    def payment_status(self, obj):
        return obj.booking.get_payment_status_display()
