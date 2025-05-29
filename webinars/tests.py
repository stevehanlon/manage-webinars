from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json

from .models import (
    Webinar, WebinarDate, Attendee, 
    WebinarBundle, BundleDate, BundleAttendee
)
from .utils import (
    process_kajabi_webhook, find_bundle_by_form_title,
    parse_webinar_date, find_bundle_date
)


class BundleModelTests(TestCase):
    def setUp(self):
        self.bundle = WebinarBundle.objects.create(
            name="WordPress and SEO Bundle",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/bundle123/activate",
            form_date_field="Bundle date",
            checkout_date_field="custom_field_bundle_date",
            error_notification_email="test@example.com"
        )
        
        self.webinar1 = Webinar.objects.create(
            name="Getting Started with WordPress",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/wp123/activate"
        )
        
        self.webinar2 = Webinar.objects.create(
            name="SEO Fundamentals",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/seo123/activate"
        )
        
        self.test_date = timezone.now() + timedelta(days=7)
        
    def test_bundle_creation(self):
        """Test that a bundle can be created successfully"""
        self.assertEqual(self.bundle.name, "WordPress and SEO Bundle")
        self.assertEqual(self.bundle.form_date_field, "Bundle date")
        self.assertFalse(self.bundle.is_deleted)
        
    def test_bundle_date_creation(self):
        """Test creating a bundle date with multiple webinars"""
        # Create webinar dates
        wp_date = WebinarDate.objects.create(
            webinar=self.webinar1,
            date_time=self.test_date
        )
        seo_date = WebinarDate.objects.create(
            webinar=self.webinar2,
            date_time=self.test_date
        )
        
        # Create bundle date
        bundle_date = BundleDate.objects.create(
            bundle=self.bundle,
            date=self.test_date.date()
        )
        bundle_date.webinar_dates.add(wp_date, seo_date)
        
        self.assertEqual(bundle_date.webinar_dates.count(), 2)
        self.assertIn(wp_date, bundle_date.webinar_dates.all())
        self.assertIn(seo_date, bundle_date.webinar_dates.all())
        
    def test_bundle_attendee_creation(self):
        """Test creating bundle attendees"""
        bundle_date = BundleDate.objects.create(
            bundle=self.bundle,
            date=self.test_date.date()
        )
        
        attendee = BundleAttendee.objects.create(
            bundle_date=bundle_date,
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        
        self.assertEqual(attendee.first_name, "John")
        self.assertEqual(str(attendee), "John Doe - john@example.com (Bundle)")
        
    def test_bundle_soft_delete(self):
        """Test soft delete functionality for bundles"""
        self.assertFalse(self.bundle.is_deleted)
        self.bundle.soft_delete()
        self.assertTrue(self.bundle.is_deleted)
        
    def test_get_webinars_on_date(self):
        """Test finding webinars that match a bundle date"""
        # Create webinar dates around the same time
        wp_date = WebinarDate.objects.create(
            webinar=self.webinar1,
            date_time=self.test_date
        )
        seo_date = WebinarDate.objects.create(
            webinar=self.webinar2,
            date_time=self.test_date + timedelta(minutes=30)
        )
        # This one should not match (too far away)
        other_date = WebinarDate.objects.create(
            webinar=self.webinar1,
            date_time=self.test_date + timedelta(hours=2)
        )
        
        bundle_date = BundleDate.objects.create(
            bundle=self.bundle,
            date=self.test_date.date()
        )
        
        matching_webinars = bundle_date.get_webinars_on_date()
        self.assertEqual(matching_webinars.count(), 2)
        self.assertIn(wp_date, matching_webinars)
        self.assertIn(seo_date, matching_webinars)
        self.assertNotIn(other_date, matching_webinars)


class WebinarDateBundleIntegrationTests(TestCase):
    def setUp(self):
        self.webinar = Webinar.objects.create(
            name="WordPress Basics",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/wp123/activate"
        )
        
        self.bundle = WebinarBundle.objects.create(
            name="WordPress Bundle",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/bundle123/activate"
        )
        
        self.test_date = timezone.now() + timedelta(days=7)
        
        self.webinar_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=self.test_date
        )
        
        self.bundle_date = BundleDate.objects.create(
            bundle=self.bundle,
            date_time=self.test_date
        )
        self.bundle_date.webinar_dates.add(self.webinar_date)
        
    def test_get_all_attendees(self):
        """Test that get_all_attendees returns both direct and bundle attendees"""
        # Create direct attendee
        direct_attendee = Attendee.objects.create(
            webinar_date=self.webinar_date,
            first_name="Direct",
            last_name="User",
            email="direct@example.com"
        )
        
        # Create bundle attendee
        bundle_attendee = BundleAttendee.objects.create(
            bundle_date=self.bundle_date,
            first_name="Bundle",
            last_name="User",
            email="bundle@example.com"
        )
        
        all_attendees = self.webinar_date.get_all_attendees()
        
        self.assertEqual(len(all_attendees), 2)
        
        # Check direct attendee
        direct = next(a for a in all_attendees if a.email == "direct@example.com")
        self.assertFalse(direct.is_bundle_attendee)
        
        # Check bundle attendee
        bundle = next(a for a in all_attendees if a.email == "bundle@example.com")
        self.assertTrue(bundle.is_bundle_attendee)
        self.assertEqual(bundle.bundle_name, "WordPress Bundle")
        
    def test_attendee_counts(self):
        """Test attendee counting with bundles"""
        # Create 2 direct attendees
        for i in range(2):
            Attendee.objects.create(
                webinar_date=self.webinar_date,
                first_name=f"Direct{i}",
                last_name="User",
                email=f"direct{i}@example.com"
            )
        
        # Create 3 bundle attendees
        for i in range(3):
            BundleAttendee.objects.create(
                bundle_date=self.bundle_date,
                first_name=f"Bundle{i}",
                last_name="User",
                email=f"bundle{i}@example.com"
            )
        
        self.assertEqual(self.webinar_date.attendee_count, 2)
        self.assertEqual(self.webinar_date.total_attendee_count, 5)


class WebhookBundleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = '/api/attendee-webhook/'  # Update with actual URL
        
        self.bundle = WebinarBundle.objects.create(
            name="WordPress and SEO Bundle",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/bundle123/activate",
            form_date_field="Bundle options",
            checkout_date_field="custom_field_bundle_dates",
            error_notification_email="test@example.com"
        )
        
        self.webinar = Webinar.objects.create(
            name="Getting Started with WordPress",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/wp123/activate"
        )
        
        self.test_date = timezone.now() + timedelta(days=7)
        
        self.bundle_date = BundleDate.objects.create(
            bundle=self.bundle,
            date_time=self.test_date
        )
        
        self.webinar_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=self.test_date
        )
        self.bundle_date.webinar_dates.add(self.webinar_date)
        
    def test_bundle_form_submission_webhook(self):
        """Test processing a Kajabi form submission for a bundle"""
        date_str = self.test_date.strftime("%d %B, %H-%M:00 BST")
        
        webhook_data = {
            "id": "test-webhook-id",
            "event": "form_submission.created",
            "payload": {
                "form_title": "WordPress and SEO Bundle",
                "First Name": "Jane",
                "Email": "jane@example.com",
                "Bundle options": date_str
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertTrue(success)
        self.assertIn("bundle attendee", message)
        
        # Check attendee was created
        attendee = BundleAttendee.objects.get(email="jane@example.com")
        self.assertEqual(attendee.first_name, "Jane")
        self.assertEqual(attendee.bundle_date, self.bundle_date)
        
    def test_bundle_purchase_webhook(self):
        """Test processing a Kajabi purchase event for a bundle"""
        date_str = self.test_date.strftime("%d %B, %H-%M:00 BST")
        
        webhook_data = {
            "id": "test-webhook-id",
            "event": "purchase.created",
            "payload": {
                "offer_title": "WordPress and SEO Bundle",
                "member_first_name": "Bob",
                "member_last_name": "Smith",
                "member_email": "bob@example.com",
                "custom_field_bundle_dates": date_str
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertTrue(success)
        self.assertIn("bundle attendee", message)
        
        # Check attendee was created
        attendee = BundleAttendee.objects.get(email="bob@example.com")
        self.assertEqual(attendee.first_name, "Bob")
        self.assertEqual(attendee.last_name, "Smith")
        
    def test_bundle_not_found(self):
        """Test webhook when bundle doesn't exist"""
        webhook_data = {
            "id": "test-webhook-id",
            "event": "form_submission.created",
            "payload": {
                "form_title": "Non-existent Bundle",
                "First Name": "Test",
                "Email": "test@example.com",
                "Bundle options": "21 August, 10-11:00 BST"
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertFalse(success)
        self.assertIn("No matching webinar or bundle found", message)
        
    def test_bundle_date_not_found(self):
        """Test webhook when bundle date doesn't match"""
        webhook_data = {
            "id": "test-webhook-id",
            "event": "form_submission.created",
            "payload": {
                "form_title": "WordPress and SEO Bundle",
                "First Name": "Test",
                "Email": "test@example.com",
                "Bundle options": "31 December, 23-00:00 BST"  # Far future date
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertFalse(success)
        self.assertIn("No matching bundle date found", message)
        
    def test_duplicate_bundle_attendee(self):
        """Test handling duplicate bundle attendee registration"""
        date_str = self.test_date.strftime("%d %B, %H-%M:00 BST")
        
        # Create existing attendee
        BundleAttendee.objects.create(
            bundle_date=self.bundle_date,
            first_name="Existing",
            last_name="User",
            email="existing@example.com"
        )
        
        webhook_data = {
            "id": "test-webhook-id",
            "event": "form_submission.created",
            "payload": {
                "form_title": "WordPress and SEO Bundle",
                "First Name": "Updated",
                "Email": "existing@example.com",
                "Bundle options": date_str
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertTrue(success)
        self.assertIn("Updated", message)
        
        # Check only one attendee exists
        self.assertEqual(BundleAttendee.objects.filter(email="existing@example.com").count(), 1)


class BundleUtilsTests(TestCase):
    def setUp(self):
        self.bundle = WebinarBundle.objects.create(
            name="WordPress Bundle",
            kajabi_grant_activation_hook_url="https://app.kajabi.com/webhooks/offers/bundle123/activate"
        )
        
        self.test_date = timezone.now() + timedelta(days=7)
        
    def test_find_bundle_by_form_title_exact_match(self):
        """Test finding bundle by exact title match"""
        result = find_bundle_by_form_title("WordPress Bundle")
        self.assertEqual(result, self.bundle)
        
    def test_find_bundle_by_form_title_partial_match(self):
        """Test finding bundle by partial title match"""
        result = find_bundle_by_form_title("WordPress Bundle Registration Form")
        self.assertEqual(result, self.bundle)
        
    def test_find_bundle_by_form_title_no_match(self):
        """Test when no bundle matches"""
        result = find_bundle_by_form_title("Python Course")
        self.assertIsNone(result)
        
    def test_parse_webinar_date_for_bundle(self):
        """Test date parsing works for bundle dates"""
        date_str = "21 August, 10-11:00 BST"
        parsed = parse_webinar_date(date_str)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.hour, 10)
        self.assertEqual(parsed.day, 21)
        
    def test_find_bundle_date(self):
        """Test finding bundle date within time window"""
        bundle_date = BundleDate.objects.create(
            bundle=self.bundle,
            date=self.test_date.date()
        )
        
        # Within 1 hour window
        result = find_bundle_date(self.bundle, self.test_date + timedelta(minutes=30))
        self.assertEqual(result, bundle_date)
        
        # Outside 1 hour window
        result = find_bundle_date(self.bundle, self.test_date + timedelta(hours=2))
        self.assertIsNone(result)


class BundleFormTests(TestCase):
    def test_bundle_date_form_webinar_filtering(self):
        """Test that BundleDateForm properly filters webinars by date"""
        from .forms import BundleDateForm
        
        # Create webinars at different times
        test_date = timezone.now() + timedelta(days=7)
        
        webinar1 = Webinar.objects.create(name="WordPress")
        webinar2 = Webinar.objects.create(name="SEO")
        webinar3 = Webinar.objects.create(name="Python")
        
        # Create webinar dates
        wd1 = WebinarDate.objects.create(
            webinar=webinar1,
            date_time=test_date
        )
        wd2 = WebinarDate.objects.create(
            webinar=webinar2,
            date_time=test_date + timedelta(minutes=30)
        )
        wd3 = WebinarDate.objects.create(
            webinar=webinar3,
            date_time=test_date + timedelta(hours=2)  # Too far away
        )
        
        # Test form with date
        form_data = {
            'date_time': test_date.strftime('%Y-%m-%dT%H:%M'),
            'webinar_dates': []
        }
        
        form = BundleDateForm(data=form_data)
        
        # Check that only nearby webinars are in queryset
        webinar_choices = form.fields['webinar_dates'].queryset
        self.assertIn(wd1, webinar_choices)
        self.assertIn(wd2, webinar_choices)
        self.assertNotIn(wd3, webinar_choices)