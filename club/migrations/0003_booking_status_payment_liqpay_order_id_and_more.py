

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0002_booking_customer_name_booking_phone_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='status',
            field=models.CharField(choices=[('pending', 'Очікує оплати'), ('confirmed', 'Підтверджено'), ('cancelled', 'Скасовано')], default='confirmed', max_length=20),
        ),
        migrations.AddField(
            model_name='payment',
            name='liqpay_order_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='status',
            field=models.CharField(default='pending', max_length=40),
        ),
        migrations.AlterField(
            model_name='payment',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
