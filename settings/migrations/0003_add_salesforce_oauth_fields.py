# Generated manually for Salesforce OAuth fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings', '0002_salesforcesettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesforcesettings',
            name='client_id',
            field=models.CharField(blank=True, help_text='Salesforce Connected App Client ID (leave blank to use default)', max_length=255),
        ),
        migrations.AddField(
            model_name='salesforcesettings',
            name='client_secret',
            field=models.CharField(blank=True, help_text='Salesforce Connected App Client Secret (leave blank to use default)', max_length=255),
        ),
    ]