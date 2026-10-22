from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django import forms
from django.core.exceptions import ValidationError
from .models import Computer, Tariff, Booking, Payment, UserProfile
from django.db import transaction
from .services import synchronize_payment_record, update_computer_statuses


class BookingAdminForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and self.instance.payment_status == 'paid':
            locked_fields = ('computer', 'tariff', 'start_time', 'end_time')
            if any(
                cleaned_data.get(field) != getattr(self.instance, field)
                for field in locked_fields
            ):
                raise ValidationError(
                    'Не можна змінювати час, комп’ютер або тариф оплаченого бронювання.'
                )
        computer = cleaned_data.get('computer')
        if computer:
            with transaction.atomic():
                cleaned_data['computer'] = Computer.objects.select_for_update().get(
                    pk=computer.pk
                )
        return cleaned_data


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


class TariffAdminForm(forms.ModelForm):
    class Meta:
        model = Tariff
        fields = '__all__'

    def clean_price_per_hour(self):
        price = self.cleaned_data['price_per_hour']
        if price < 0:
            raise forms.ValidationError('Ціна за годину не може бути від’ємною.')
        return price


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    form = TariffAdminForm
    list_display = ('id', 'name', 'price_per_hour')
    list_filter = ('price_per_hour',)
    search_fields = ('name',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingAdminForm
    list_display = (
        'id',
        'customer_name',
        'phone',
        'computer',
        'tariff',
        'start_time',
        'end_time',
        'status',
        'payment_method',
        'payment_status',
        'duration',
    )

    list_filter = (
        'status',
        'payment_method',
        'payment_status',
        'tariff',
        'start_time',
    )
    search_fields = (
        'customer_name',
        'phone',
        'user__username',
        'computer__name',
    )

    @admin.display(description='Тривалість')
    def save_model(self, request, obj, form, change):
        if obj.payment_method == 'card' and obj.status != 'cancelled':
            obj.status = (
                'confirmed' if obj.payment_status == 'paid' else 'pending'
            )
        super().save_model(request, obj, form, change)
        synchronize_payment_record(obj)
        update_computer_statuses()

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
        'status',
        'is_paid',
        'amount',
        'paid_at',
    )
    list_filter = ('status', 'is_paid')
    search_fields = (
        'booking__customer_name',
        'booking__phone',
        'booking__user__username',
        'booking__computer__name',
    )
    list_select_related = ('booking', 'booking__computer', 'booking__user')
    readonly_fields = ('booking', 'amount', 'paid_at', 'is_paid', 'status')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(
        description='\u0421\u0442\u0430\u0442\u0443\u0441 \u043e\u043f\u043b\u0430\u0442\u0438',
        ordering='status',
    )
    def payment_status(self, obj):
        if obj.booking_id:
            return obj.booking.get_payment_status_display()
        return obj.status
