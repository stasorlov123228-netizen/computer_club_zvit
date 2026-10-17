

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='customer_name',
            field=models.CharField(default='Невідомий клієнт', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='booking',
            name='phone',
            field=models.CharField(default='Невідомий клієнт', max_length=20),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='booking',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
    ]
