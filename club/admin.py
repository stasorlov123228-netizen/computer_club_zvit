from django.contrib import admin
from .models import Computer, Tariff, Booking, Payment
from .views import update_computer_statuses


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
    list_display = ('id', 'booking', 'amount', 'is_paid', 'paid_at')
    list_filter = ('is_paid',)
