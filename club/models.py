
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse


class Computer(models.Model):
    manual_occupied = models.BooleanField(default=False)
    name = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Вільний'),
            ('occupied', 'Зайнятий'),
            ('maintenance', 'На обслуговуванні'),
        ],
        default='available'
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('computer_detail', kwargs={'pk': self.pk})


class Tariff(models.Model):
    name = models.CharField(max_length=100)
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('tariff_detail', kwargs={'pk': self.pk})


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username




class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Очікує оплати'),
        ('confirmed', 'Підтверджено'),
        ('cancelled', 'Скасовано'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('card', 'СПЛАЧЕНО КАРТКОЮ'),
        ('cash', 'ОПЛАТА В КЛУБІ'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('paid', 'ОПЛАЧЕНО'),
        ('unpaid', 'НЕ ОПЛАЧЕНО'),
    ]

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )


    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    customer_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    computer = models.ForeignKey(Computer, on_delete=models.CASCADE)
    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='confirmed'
    )

    def clean(self):
        super().clean()

        if (
            self.start_time
            and self.end_time
            and self.end_time <= self.start_time
        ):
            raise ValidationError({
                'end_time': 'Час завершення має бути пізніше за час початку.'
            })

        if (
            self.status == 'cancelled'
            or not self.computer_id
            or not self.start_time
            or not self.end_time
        ):
            return

        computer = self.computer
        if computer.status == 'maintenance' or computer.manual_occupied:
            raise ValidationError({
                'computer': 'Цей ПК зараз недоступний.'
            })

        conflicts = Booking.objects.filter(
            computer_id=self.computer_id,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(status='cancelled')
        if self.pk:
            conflicts = conflicts.exclude(pk=self.pk)
        if conflicts.exists():
            raise ValidationError({
                'computer': 'ПК уже заброньований на обраний час.'
            })

    def __str__(self):
        return f'{self.customer_name} - {self.computer.name}'

    def get_absolute_url(self):
        return reverse('booking_detail', kwargs={'pk': self.pk})


class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid_at = models.DateTimeField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=40, default='pending')

    def __str__(self):
        return f'Оплата №{self.pk}'
