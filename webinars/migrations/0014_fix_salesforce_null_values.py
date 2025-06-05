# Fix potential NULL values in Salesforce fields

from django.db import migrations


def fix_null_salesforce_fields(apps, schema_editor):
    """Set NULL Salesforce fields to empty strings."""
    Attendee = apps.get_model('webinars', 'Attendee')
    OnDemandAttendee = apps.get_model('webinars', 'OnDemandAttendee')
    BundleAttendee = apps.get_model('webinars', 'BundleAttendee')
    
    # Fix NULL values in all attendee models
    for model in [Attendee, OnDemandAttendee, BundleAttendee]:
        model.objects.filter(salesforce_account_id__isnull=True).update(salesforce_account_id='')
        model.objects.filter(salesforce_contact_id__isnull=True).update(salesforce_contact_id='')
        model.objects.filter(salesforce_task_id__isnull=True).update(salesforce_task_id='')
        model.objects.filter(salesforce_sync_error__isnull=True).update(salesforce_sync_error='')


class Migration(migrations.Migration):

    dependencies = [
        ('webinars', '0013_add_salesforce_integration'),
    ]

    operations = [
        migrations.RunPython(fix_null_salesforce_fields, migrations.RunPython.noop),
    ]