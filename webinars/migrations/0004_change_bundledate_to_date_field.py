# Generated manually to rename date_time to date field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webinars', '0003_webinarbundle_bundledate_bundleattendee'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bundledate',
            old_name='date_time',
            new_name='date_temp',
        ),
        migrations.AlterField(
            model_name='bundledate',
            name='date_temp',
            field=models.DateField(),
        ),
        migrations.RenameField(
            model_name='bundledate',
            old_name='date_temp',
            new_name='date',
        ),
    ]