from django.db import migrations


def rename_default_tariff(apps, schema_editor):
    Tariff = apps.get_model('club', 'Tariff')
    Tariff.objects.using(schema_editor.connection.alias).filter(
        name__iexact='DEFAULT',
    ).update(name='STANDART')


class Migration(migrations.Migration):

    dependencies = [
        ('club', '0011_alter_payment_status'),
    ]

    operations = [
        migrations.RunPython(rename_default_tariff, migrations.RunPython.noop),
    ]
