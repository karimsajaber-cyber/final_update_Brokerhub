from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from brokers.models import BrokerProfile
from core.models import Category, Platform
from locations.models import City
from requests.models import BrokerQuote, QuoteRequest


class ReviewAccessTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Jerusalem')
        self.category = Category.objects.create(name='Phones')
        self.platform = Platform.objects.create(name='Amazon', category=self.category)

        self.customer = User.objects.create_user(
            username='review_customer',
            password='pass1234',
            role='customer',
            phone='0599111111',
        )
        self.other_customer = User.objects.create_user(
            username='other_customer',
            password='pass1234',
            role='customer',
            phone='0599222222',
        )
        self.broker_user = User.objects.create_user(
            username='review_broker',
            password='pass1234',
            role='broker',
            phone='0599333333',
        )
        self.broker = BrokerProfile.objects.create(
            user=self.broker_user,
            business_name='Gamma Broker',
            city=self.city,
            whatsapp_number='0599444444',
        )

    def login_session(self, user, role):
        session = self.client.session
        session['user_id'] = user.id
        session['role'] = role
        session.save()

    def create_request_and_quote(self, **request_overrides):
        request_data = {
            'customer': self.customer,
            'platform': self.platform,
            'city': self.city,
            'product_name': 'Galaxy S24',
            'notes': 'Customer request',
            'broker': self.broker,
            'status': 'completed',
        }
        request_data.update(request_overrides)
        request_item = QuoteRequest.objects.create(**request_data)
        quote = BrokerQuote.objects.create(
            quote_request=request_item,
            broker=self.broker,
            total_price=Decimal('300.00'),
            delivery_days=4,
            status='accepted',
        )
        return request_item, quote

    def test_other_customer_cannot_open_review_page(self):
        _, quote = self.create_request_and_quote()

        self.login_session(self.other_customer, 'customer')
        response = self.client.get(reverse('add_review', args=[quote.id]))

        self.assertEqual(response.status_code, 404)

    def test_customer_cannot_review_before_completion(self):
        request_item, quote = self.create_request_and_quote(status='accepted')

        self.login_session(self.customer, 'customer')
        response = self.client.get(reverse('add_review', args=[quote.id]))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/requests/my?notice=', response.url)
        request_item.refresh_from_db()
        self.assertEqual(request_item.status, 'accepted')

    def test_review_page_backfills_old_zero_price_from_request_notes(self):
        request_item, quote = self.create_request_and_quote(
            notes='Customer request\n[Price: $220] [Delivery: 6 days]',
        )
        quote.total_price = Decimal('0')
        quote.delivery_days = 0
        quote.save()

        self.login_session(self.customer, 'customer')
        response = self.client.get(reverse('add_review', args=[quote.id]))

        self.assertEqual(response.status_code, 200)
        quote.refresh_from_db()
        request_item.refresh_from_db()
        self.assertEqual(quote.total_price, Decimal('220'))
        self.assertEqual(quote.delivery_days, 6)
