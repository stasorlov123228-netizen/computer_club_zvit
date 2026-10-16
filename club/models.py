
from django.db import models
from django.contrib.auth.models import User


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


class Tariff(models.Model):
    name = models.CharField(max_length=100)
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name


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

    def __str__(self):
        return f'{self.customer_name} — {self.computer.name}'


class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid_at = models.DateTimeField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    liqpay_order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )
    status = models.CharField(max_length=40, default='pending')

    def __str__(self):
        return f'Оплата №{self.pk}'


    def __str__(self):
        return f'Оплата №{self.pk}'
