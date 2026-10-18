from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0007_create_booking_payments'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='payment',
            name='liqpay_order_id',
        ),
    ]
