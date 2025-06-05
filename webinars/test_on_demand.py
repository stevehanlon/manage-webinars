"""
Unit tests for on-demand webinar functionality.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

from .models import Webinar, WebinarDate, Attendee, OnDemandAttendee
from .utils import (
    parse_webinar_date, 
    create_on_demand_attendee,
    process_kajabi_webhook
)


class OnDemandParsingTests(TestCase):
    """Test parsing of on-demand date strings."""
    
    def test_parse_on_demand_lowercase(self):
        """Test parsing 'on demand' in lowercase."""
        result = parse_webinar_date("on demand")
        self.assertEqual(result, 'on_demand')
    
    def test_parse_on_demand_uppercase(self):
        """Test parsing 'ON DEMAND' in uppercase."""
        result = parse_webinar_date("ON DEMAND")
        self.assertEqual(result, 'on_demand')
    
    def test_parse_on_demand_mixed_case(self):
        """Test parsing 'On Demand' in mixed case."""
        result = parse_webinar_date("On Demand")
        self.assertEqual(result, 'on_demand')
    
    def test_parse_on_demand_with_extra_text(self):
        """Test parsing with additional text."""
        result = parse_webinar_date("On Demand Access")
        self.assertEqual(result, 'on_demand')
        
        result = parse_webinar_date("Get on demand recordings")
        self.assertEqual(result, 'on_demand')
    
    def test_parse_regular_date_still_works(self):
        """Test that regular date parsing still works."""
        result = parse_webinar_date("21 August, 10-11:00 BST")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.day, 21)
        self.assertEqual(result.hour, 10)
    
    def test_parse_invalid_date(self):
        """Test parsing invalid date string."""
        result = parse_webinar_date("invalid date string")
        self.assertIsNone(result)


class OnDemandModelTests(TestCase):
    """Test on-demand attendee model functionality."""
    
    def setUp(self):
        self.webinar = Webinar.objects.create(
            name="Test Webinar",
            kajabi_grant_activation_hook_url="https://example.com/webhook"
        )
    
    def test_on_demand_attendee_creation(self):
        """Test creating an on-demand attendee."""
        attendee = OnDemandAttendee.objects.create(
            webinar=self.webinar,
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        
        self.assertEqual(attendee.webinar, self.webinar)
        self.assertEqual(attendee.first_name, "John")
        self.assertEqual(attendee.last_name, "Doe")
        self.assertEqual(attendee.email, "john@example.com")
        self.assertIsNone(attendee.activation_sent_at)
        self.assertIsNone(attendee.activation_success)
    
    def test_on_demand_attendee_activation_status(self):
        """Test activation status property."""
        attendee = OnDemandAttendee.objects.create(
            webinar=self.webinar,
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        
        # Initially pending
        self.assertEqual(attendee.activation_status, "Pending")
        
        # After successful activation
        attendee.activation_sent_at = timezone.now()
        attendee.activation_success = True
        self.assertEqual(attendee.activation_status, "Sent")
        
        # After failed activation
        attendee.activation_success = False
        attendee.activation_error = "Test error"
        self.assertEqual(attendee.activation_status, "Failed")


class OnDemandUtilsTests(TestCase):
    """Test utility functions for on-demand webinars."""
    
    def setUp(self):
        self.webinar = Webinar.objects.create(
            name="Test Webinar",
            kajabi_grant_activation_hook_url="https://example.com/webhook"
        )
    
    def test_create_on_demand_attendee_creates_new(self):
        """Test creating a new on-demand attendee."""
        # Ensure no existing on-demand attendees
        self.assertEqual(OnDemandAttendee.objects.filter(webinar=self.webinar).count(), 0)
        
        attendee, created = create_on_demand_attendee(
            self.webinar, "John", "Doe", "john@example.com"
        )
        
        self.assertTrue(created)
        self.assertEqual(attendee.webinar, self.webinar)
        self.assertEqual(attendee.first_name, "John")
        self.assertEqual(attendee.last_name, "Doe")
        self.assertEqual(attendee.email, "john@example.com")
        self.assertEqual(OnDemandAttendee.objects.filter(webinar=self.webinar).count(), 1)
    
    def test_create_on_demand_attendee_finds_existing(self):
        """Test finding an existing on-demand attendee."""
        # Create existing on-demand attendee
        existing_attendee = OnDemandAttendee.objects.create(
            webinar=self.webinar,
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        
        attendee, created = create_on_demand_attendee(
            self.webinar, "John", "Smith", "john@example.com"
        )
        
        self.assertFalse(created)
        self.assertEqual(attendee, existing_attendee)
        self.assertEqual(OnDemandAttendee.objects.filter(webinar=self.webinar).count(), 1)
    
    def test_create_on_demand_attendee_restores_deleted(self):
        """Test that soft-deleted on-demand attendees are restored."""
        # Create and soft-delete an on-demand attendee
        deleted_attendee = OnDemandAttendee.objects.create(
            webinar=self.webinar,
            first_name="John",
            last_name="Doe", 
            email="john@example.com"
        )
        deleted_attendee.soft_delete()
        
        attendee, created = create_on_demand_attendee(
            self.webinar, "John", "Smith", "john@example.com"
        )
        
        self.assertFalse(created)
        self.assertEqual(attendee, deleted_attendee)
        self.assertFalse(attendee.is_deleted)
        self.assertEqual(attendee.last_name, "Smith")  # Updated name


class OnDemandWebhookTests(TestCase):
    """Test webhook processing for on-demand webinars."""
    
    def setUp(self):
        self.webinar = Webinar.objects.create(
            name="Test Webinar",
            kajabi_grant_activation_hook_url="https://example.com/webhook",
            form_date_field="Webinar Date",
            checkout_date_field="webinar_date",
            error_notification_email="test@example.com"
        )
    
    @patch('webinars.activation_service.activate_attendee')
    def test_form_submission_on_demand_webhook(self, mock_activate):
        """Test processing Kajabi form submission for on-demand webinar."""
        mock_activate.return_value = (True, "Activation successful")
        
        webhook_data = {
            "event": "form_submission.created",
            "payload": {
                "form_title": "Test Webinar",
                "First Name": "John",
                "Email": "john@example.com",
                "Webinar Date": "on demand"
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertTrue(success)
        self.assertIn("on-demand", message.lower())
        
        # Check on-demand attendee was created
        attendee = OnDemandAttendee.objects.get(email="john@example.com")
        self.assertEqual(attendee.first_name, "John")
        self.assertEqual(attendee.webinar, self.webinar)
        
        # Check activation was called
        mock_activate.assert_called_once_with(attendee)
    
    @patch('webinars.activation_service.activate_attendee')
    def test_purchase_on_demand_webhook(self, mock_activate):
        """Test processing Kajabi purchase for on-demand webinar."""
        mock_activate.return_value = (True, "Activation successful")
        
        webhook_data = {
            "event": "purchase.created",
            "payload": {
                "offer_title": "Test Webinar",
                "member_first_name": "Jane",
                "member_last_name": "Doe",
                "member_email": "jane@example.com",
                "webinar_date": "On Demand Access"
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertTrue(success)
        self.assertIn("on-demand", message.lower())
        
        # Check on-demand attendee was created
        attendee = OnDemandAttendee.objects.get(email="jane@example.com")
        self.assertEqual(attendee.first_name, "Jane")
        self.assertEqual(attendee.last_name, "Doe")
        self.assertEqual(attendee.webinar, self.webinar)
        
        # Check activation was called
        mock_activate.assert_called_once_with(attendee)
    
    @patch('webinars.activation_service.activate_attendee')
    def test_on_demand_activation_failure(self, mock_activate):
        """Test handling of activation failure for on-demand attendee."""
        mock_activate.return_value = (False, "Activation failed")
        
        webhook_data = {
            "event": "form_submission.created",
            "payload": {
                "form_title": "Test Webinar",
                "First Name": "Test",
                "Email": "test@example.com",
                "Webinar Date": "on demand"
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertTrue(success)  # Webhook processing succeeds even if activation fails
        self.assertIn("on-demand", message.lower())
        
        # Check on-demand attendee was created
        attendee = OnDemandAttendee.objects.get(email="test@example.com")
        self.assertEqual(attendee.webinar, self.webinar)
        
        # Check activation was attempted
        mock_activate.assert_called_once_with(attendee)
    
    @patch('webinars.activation_service.activate_attendee')
    def test_on_demand_duplicate_attendee(self, mock_activate):
        """Test handling duplicate on-demand attendee registration."""
        mock_activate.return_value = (True, "Activation successful")
        # Create existing on-demand attendee
        existing_attendee = OnDemandAttendee.objects.create(
            webinar=self.webinar,
            first_name="Original",
            last_name="User",
            email="test@example.com"
        )
        
        webhook_data = {
            "event": "form_submission.created",
            "payload": {
                "form_title": "Test Webinar",
                "First Name": "Updated",
                "Email": "test@example.com",
                "Webinar Date": "on demand"
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        self.assertTrue(success)
        self.assertIn("Updated", message)
        
        # Check only one on-demand attendee exists
        attendees = OnDemandAttendee.objects.filter(email="test@example.com")
        self.assertEqual(attendees.count(), 1)


class OnDemandViewTests(TestCase):
    """Test view functionality for on-demand webinars."""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')
        
        self.webinar = Webinar.objects.create(
            name="Test Webinar",
            kajabi_grant_activation_hook_url="https://example.com/webhook"
        )
        
        # Create an on-demand attendee
        self.on_demand_attendee = OnDemandAttendee.objects.create(
            webinar=self.webinar,
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
    
    def test_webinar_detail_shows_on_demand_attendees(self):
        """Test that webinar detail view shows on-demand attendees."""
        url = reverse('webinar_detail', args=[self.webinar.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "On-Demand Attendees")
        self.assertContains(response, "test@example.com")
        self.assertContains(response, "1 attendee")
        
        # Check that the on-demand section is shown
        self.assertContains(response, "on-demand access to the latest webinar recordings")


class OnDemandIntegrationTests(TestCase):
    """Integration tests for on-demand webinar functionality."""
    
    def setUp(self):
        self.webinar = Webinar.objects.create(
            name="WordPress Masterclass",
            kajabi_grant_activation_hook_url="https://example.com/webhook",
            form_date_field="Access Type",
            error_notification_email="test@example.com"
        )
    
    @patch('webinars.activation_service.requests.post')
    def test_end_to_end_on_demand_flow(self, mock_post):
        """Test complete end-to-end flow for on-demand webinar."""
        # Mock successful Kajabi activation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Simulate webhook from Kajabi
        webhook_data = {
            "event": "form_submission.created",
            "payload": {
                "form_title": "WordPress Masterclass",
                "First Name": "Sarah",
                "Email": "sarah@example.com",
                "Access Type": "on demand recordings"
            }
        }
        
        success, message, attendee_id = process_kajabi_webhook(webhook_data, None)
        
        # Verify webhook processing succeeded
        self.assertTrue(success)
        self.assertIn("on-demand", message.lower())
        
        # Verify on-demand attendee was created
        attendee = OnDemandAttendee.objects.get(email="sarah@example.com")
        self.assertEqual(attendee.first_name, "Sarah")
        self.assertEqual(attendee.webinar, self.webinar)
        
        # Verify Kajabi activation was called
        mock_post.assert_called_once()
        
        # Verify activation status
        self.assertIsNotNone(attendee.activation_sent_at)
        self.assertTrue(attendee.activation_success)
    
    @patch('webinars.activation_service.activate_attendee')
    def test_multiple_on_demand_attendees_same_webinar(self, mock_activate):
        """Test that multiple on-demand attendees are created for the same webinar."""
        mock_activate.return_value = (True, "Activation successful")
        # Process first attendee
        webhook_data1 = {
            "event": "form_submission.created",
            "payload": {
                "form_title": "WordPress Masterclass",
                "First Name": "User1",
                "Email": "user1@example.com",
                "Access Type": "on demand"
            }
        }
        
        success1, _, _ = process_kajabi_webhook(webhook_data1, None)
        self.assertTrue(success1)
        
        # Process second attendee
        webhook_data2 = {
            "event": "form_submission.created",
            "payload": {
                "form_title": "WordPress Masterclass",
                "First Name": "User2",
                "Email": "user2@example.com",
                "Access Type": "on demand"
            }
        }
        
        success2, _, _ = process_kajabi_webhook(webhook_data2, None)
        self.assertTrue(success2)
        
        # Verify both on-demand attendees were created for the same webinar
        attendee1 = OnDemandAttendee.objects.get(email="user1@example.com")
        attendee2 = OnDemandAttendee.objects.get(email="user2@example.com")
        
        self.assertEqual(attendee1.webinar, self.webinar)
        self.assertEqual(attendee2.webinar, self.webinar)
        self.assertEqual(attendee1.webinar, attendee2.webinar)
        
        # Verify both attendees exist as separate records
        on_demand_attendees = OnDemandAttendee.objects.filter(webinar=self.webinar)
        self.assertEqual(on_demand_attendees.count(), 2)