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

from .models import Webinar, WebinarDate, Attendee
from .utils import (
    parse_webinar_date, 
    find_or_create_on_demand_webinar_date,
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
    """Test on-demand webinar model functionality."""
    
    def setUp(self):
        self.webinar = Webinar.objects.create(
            name="Test Webinar",
            kajabi_grant_activation_hook_url="https://example.com/webhook"
        )
    
    def test_on_demand_webinar_date_creation(self):
        """Test creating an on-demand webinar date."""
        webinar_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now(),
            on_demand=True
        )
        
        self.assertTrue(webinar_date.on_demand)
        self.assertEqual(str(webinar_date), "Test Webinar - On Demand")
    
    def test_regular_webinar_date_string(self):
        """Test string representation of regular webinar date."""
        webinar_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now(),
            on_demand=False
        )
        
        self.assertFalse(webinar_date.on_demand)
        self.assertIn("Test Webinar -", str(webinar_date))
        self.assertNotIn("On Demand", str(webinar_date))
    
    def test_attendee_needs_activation_on_demand(self):
        """Test that on-demand attendees need immediate activation."""
        on_demand_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now(),
            on_demand=True
        )
        
        attendee = Attendee.objects.create(
            webinar_date=on_demand_date,
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        
        self.assertTrue(attendee.needs_activation)
    
    def test_attendee_needs_activation_regular_future(self):
        """Test that regular future attendees don't need activation yet."""
        future_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now() + timedelta(days=1),
            on_demand=False
        )
        
        attendee = Attendee.objects.create(
            webinar_date=future_date,
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        
        self.assertFalse(attendee.needs_activation)
    
    def test_attendee_can_register_zoom_on_demand(self):
        """Test that on-demand attendees cannot register for Zoom."""
        on_demand_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now(),
            on_demand=True,
            zoom_meeting_id="123456789"
        )
        
        attendee = Attendee.objects.create(
            webinar_date=on_demand_date,
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        
        # Even with zoom_meeting_id, on-demand attendees can't register
        self.assertFalse(attendee.can_register_zoom)
    
    def test_attendee_can_register_zoom_regular(self):
        """Test that regular attendees can register for Zoom when appropriate."""
        regular_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now() + timedelta(days=1),
            on_demand=False,
            zoom_meeting_id="123456789"
        )
        
        attendee = Attendee.objects.create(
            webinar_date=regular_date,
            first_name="Test",
            last_name="User",
            email="test@example.com"
        )
        
        # Regular attendees with Zoom meeting can register
        self.assertTrue(attendee.can_register_zoom)


class OnDemandUtilsTests(TestCase):
    """Test utility functions for on-demand webinars."""
    
    def setUp(self):
        self.webinar = Webinar.objects.create(
            name="Test Webinar",
            kajabi_grant_activation_hook_url="https://example.com/webhook"
        )
    
    def test_find_or_create_on_demand_creates_new(self):
        """Test creating a new on-demand webinar date."""
        # Ensure no existing on-demand dates
        self.assertEqual(self.webinar.active_dates().filter(on_demand=True).count(), 0)
        
        webinar_date = find_or_create_on_demand_webinar_date(self.webinar)
        
        self.assertTrue(webinar_date.on_demand)
        self.assertEqual(webinar_date.webinar, self.webinar)
        self.assertEqual(self.webinar.active_dates().filter(on_demand=True).count(), 1)
    
    def test_find_or_create_on_demand_finds_existing(self):
        """Test finding an existing on-demand webinar date."""
        # Create existing on-demand date
        existing_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now(),
            on_demand=True
        )
        
        webinar_date = find_or_create_on_demand_webinar_date(self.webinar)
        
        self.assertEqual(webinar_date, existing_date)
        self.assertEqual(self.webinar.active_dates().filter(on_demand=True).count(), 1)
    
    def test_find_or_create_on_demand_ignores_deleted(self):
        """Test that soft-deleted on-demand dates are ignored."""
        # Create and soft-delete an on-demand date
        deleted_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now(),
            on_demand=True
        )
        deleted_date.soft_delete()
        
        webinar_date = find_or_create_on_demand_webinar_date(self.webinar)
        
        self.assertNotEqual(webinar_date, deleted_date)
        self.assertTrue(webinar_date.on_demand)
        self.assertFalse(webinar_date.is_deleted)


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
        
        # Check attendee was created
        attendee = Attendee.objects.get(email="john@example.com")
        self.assertEqual(attendee.first_name, "John")
        self.assertTrue(attendee.webinar_date.on_demand)
        
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
        
        # Check attendee was created
        attendee = Attendee.objects.get(email="jane@example.com")
        self.assertEqual(attendee.first_name, "Jane")
        self.assertEqual(attendee.last_name, "Doe")
        self.assertTrue(attendee.webinar_date.on_demand)
        
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
        
        # Check attendee was created
        attendee = Attendee.objects.get(email="test@example.com")
        self.assertTrue(attendee.webinar_date.on_demand)
        
        # Check activation was attempted
        mock_activate.assert_called_once_with(attendee)
    
    @patch('webinars.activation_service.activate_attendee')
    def test_on_demand_duplicate_attendee(self, mock_activate):
        """Test handling duplicate on-demand attendee registration."""
        mock_activate.return_value = (True, "Activation successful")
        # Create existing attendee
        existing_date = find_or_create_on_demand_webinar_date(self.webinar)
        existing_attendee = Attendee.objects.create(
            webinar_date=existing_date,
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
        
        # Check only one attendee exists
        attendees = Attendee.objects.filter(email="test@example.com")
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
        
        self.on_demand_date = WebinarDate.objects.create(
            webinar=self.webinar,
            date_time=timezone.now(),
            on_demand=True
        )
    
    def test_on_demand_date_detail_view(self):
        """Test that on-demand date detail view displays correctly."""
        url = reverse('webinar_date_detail', args=[self.on_demand_date.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "On Demand")
        self.assertContains(response, "On-Demand Access")
        self.assertContains(response, "Not applicable for on-demand")
        
        # Check that inappropriate buttons are hidden
        self.assertNotContains(response, "Create Zoom Webinar")
        self.assertNotContains(response, "Send Calendar Invite")
    
    @patch('webinars.activation_service.activate_attendee')
    def test_direct_webhook_on_demand(self, mock_activate):
        """Test direct webhook API for on-demand webinars."""
        mock_activate.return_value = (True, "Activation successful")
        
        url = reverse('attendee_webhook')
        data = {
            'webinar_date_id': self.on_demand_date.id,
            'first_name': 'Direct',
            'last_name': 'User',
            'email': 'direct@example.com'
        }
        
        response = self.client.post(url, data, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('on-demand', response_data['message'].lower())
        
        # Check attendee was created
        attendee = Attendee.objects.get(email='direct@example.com')
        self.assertTrue(attendee.webinar_date.on_demand)
        
        # Check activation was called
        mock_activate.assert_called_once_with(attendee)


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
        
        # Verify attendee was created
        attendee = Attendee.objects.get(email="sarah@example.com")
        self.assertEqual(attendee.first_name, "Sarah")
        self.assertTrue(attendee.webinar_date.on_demand)
        
        # Verify Kajabi activation was called
        mock_post.assert_called_once()
        
        # Verify activation status
        self.assertIsNotNone(attendee.activation_sent_at)
        self.assertTrue(attendee.activation_success)
        
        # Verify on-demand date was created automatically
        on_demand_dates = self.webinar.active_dates().filter(on_demand=True)
        self.assertEqual(on_demand_dates.count(), 1)
        self.assertEqual(str(on_demand_dates.first()), "WordPress Masterclass - On Demand")
    
    @patch('webinars.activation_service.activate_attendee')
    def test_multiple_on_demand_attendees_same_date(self, mock_activate):
        """Test that multiple on-demand attendees use the same on-demand date."""
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
        
        # Verify both attendees use the same on-demand date
        attendee1 = Attendee.objects.get(email="user1@example.com")
        attendee2 = Attendee.objects.get(email="user2@example.com")
        
        self.assertEqual(attendee1.webinar_date, attendee2.webinar_date)
        self.assertTrue(attendee1.webinar_date.on_demand)
        
        # Verify only one on-demand date was created
        on_demand_dates = self.webinar.active_dates().filter(on_demand=True)
        self.assertEqual(on_demand_dates.count(), 1)