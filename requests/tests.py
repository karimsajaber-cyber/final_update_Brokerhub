from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from brokers.models import BrokerProfile
from core.models import Category, Platform
from locations.models import City
from requests.models import BrokerQuote, QuoteRequest


class RequestFlowTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Hebron')
        self.category = Category.objects.create(name='Electronics')
        self.platform = Platform.objects.create(name='Amazon', category=self.category)

        self.customer = User.objects.create_user(
            username='customer1',
            password='pass1234',
            role='customer',
            phone='0599000001',
        )
        self.other_customer = User.objects.create_user(
            username='customer2',
            password='pass1234',
            role='customer',
            phone='0599000002',
        )
        self.broker_user = User.objects.create_user(
            username='broker1',
            password='pass1234',
            role='broker',
            phone='0599000010',
        )
        self.other_broker_user = User.objects.create_user(
            username='broker2',
            password='pass1234',
            role='broker',
            phone='0599000020',
        )

        self.broker = BrokerProfile.objects.create(
            user=self.broker_user,
            business_name='Alpha Broker',
            city=self.city,
            whatsapp_number='0599123456',
        )
        self.other_broker = BrokerProfile.objects.create(
            user=self.other_broker_user,
            business_name='Beta Broker',
            city=self.city,
            whatsapp_number='0599654321',
        )

    def login_session(self, user, role):
        session = self.client.session
        session['user_id'] = user.id
        session['role'] = role
        session.save()

    def create_request(self, **overrides):
        data = {
            'customer': self.customer,
            'platform': self.platform,
            'city': self.city,
            'product_name': 'iPhone 15',
            'notes': 'Need the US version',
            'broker': self.broker,
            'status': 'pending',
        }
        data.update(overrides)
        return QuoteRequest.objects.create(**data)

    def test_dashboard_shows_only_requests_assigned_to_logged_in_broker(self):
        own_request = self.create_request(product_name='Own Request', broker=self.broker)
        self.create_request(
            product_name='Other Broker Request',
            broker=self.other_broker,
            customer=self.other_customer,
        )

        self.login_session(self.broker_user, 'broker')
        response = self.client.get(reverse('broker_dashboard'))

        request_ids = [item['request'].id for item in response.context['requests_data']]
        self.assertEqual(request_ids, [own_request.id])

    def test_accept_creates_real_quote_and_completion_keeps_price(self):
        request_item = self.create_request()

        self.login_session(self.broker_user, 'broker')
        accept_response = self.client.post(
            reverse('broker_request_details', args=[request_item.id]),
            {
                'action_type': 'accept',
                'price': '150.00',
                'delivery_days': '3',
            },
        )

        self.assertEqual(accept_response.status_code, 302)
        request_item.refresh_from_db()
        self.assertEqual(request_item.status, 'accepted')

        quote = BrokerQuote.objects.get(quote_request=request_item, broker=self.broker)
        self.assertEqual(quote.total_price, Decimal('150.00'))
        self.assertEqual(quote.delivery_days, 3)
        self.assertEqual(quote.status, 'accepted')

        complete_response = self.client.post(
            reverse('broker_request_details', args=[request_item.id]),
            {'action_type': 'complete'},
        )

        self.assertEqual(complete_response.status_code, 302)
        request_item.refresh_from_db()
        quote.refresh_from_db()

        self.assertEqual(request_item.status, 'completed')
        self.assertEqual(quote.total_price, Decimal('150.00'))

    def test_my_requests_switches_from_contact_to_rating_by_status(self):
        request_item = self.create_request(status='accepted')
        BrokerQuote.objects.create(
            quote_request=request_item,
            broker=self.broker,
            total_price=Decimal('220.00'),
            delivery_days=5,
            status='accepted',
        )

        self.login_session(self.customer, 'customer')

        accepted_response = self.client.get(reverse('my_requests'))
        accepted_item = accepted_response.context['customer_requests'][0]
        self.assertTrue(accepted_item.can_contact_broker)
        self.assertFalse(accepted_item.can_rate_broker)

        request_item.status = 'completed'
        request_item.save()

        completed_response = self.client.get(reverse('my_requests'))
        completed_item = completed_response.context['customer_requests'][0]
        self.assertFalse(completed_item.can_contact_broker)
        self.assertTrue(completed_item.can_rate_broker)

    def test_broker_can_accept_quoted_request_and_customer_gets_rate_link_after_completion(self):
        request_item = self.create_request(status='quoted')
        BrokerQuote.objects.create(
            quote_request=request_item,
            broker=self.broker,
            total_price=Decimal('175.00'),
            delivery_days=2,
            status='sent',
        )

        self.login_session(self.broker_user, 'broker')
        accept_response = self.client.post(
            reverse('broker_request_details', args=[request_item.id]),
            {
                'action_type': 'accept',
                'price': '175.00',
                'delivery_days': '2',
            },
        )
        self.assertEqual(accept_response.status_code, 302)

        complete_response = self.client.post(
            reverse('broker_request_details', args=[request_item.id]),
            {'action_type': 'complete'},
        )
        self.assertEqual(complete_response.status_code, 302)

        self.login_session(self.customer, 'customer')
        response = self.client.get(reverse('my_requests'))
        request_context = response.context['customer_requests'][0]

        self.assertTrue(request_context.can_rate_broker)
        self.assertIsNotNone(request_context.review_quote_id)
