

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0004_booking_payment_method_booking_payment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='computer',
            name='manual_occupied',
            field=models.BooleanField(default=False),
        ),
    ]
