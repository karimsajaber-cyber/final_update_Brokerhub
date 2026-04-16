from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from brokers.models import BrokerPlatform, BrokerProfile
from core.models import Category, Platform
from locations.models import City


class BrokerFilterTests(TestCase):
    def setUp(self):
        self.city_one = City.objects.create(name='Hebron')
        self.city_two = City.objects.create(name='Jerusalem')

        self.category_electronics = Category.objects.create(name='Electronics')
        self.category_fashion = Category.objects.create(name='Fashion')

        self.platform_amazon = Platform.objects.create(name='Amazon', category=self.category_electronics)
        self.platform_shein = Platform.objects.create(name='Shein', category=self.category_fashion)

        self.user_one = User.objects.create_user(
            username='broker_a',
            password='pass1234',
            role='broker',
            phone='0599000100',
            first_name='Ahmad',
            last_name='Saleh',
        )
        self.user_two = User.objects.create_user(
            username='broker_b',
            password='pass1234',
            role='broker',
            phone='0599000200',
            first_name='Lina',
            last_name='Nasser',
        )

        self.broker_one = BrokerProfile.objects.create(
            user=self.user_one,
            business_name='Alpha Trade',
            city=self.city_one,
            whatsapp_number='0599111000',
            description='Electronics broker',
        )
        self.broker_two = BrokerProfile.objects.create(
            user=self.user_two,
            business_name='Style Hub',
            city=self.city_two,
            whatsapp_number='0599222000',
            description='Fashion broker',
        )

        BrokerPlatform.objects.create(broker=self.broker_one, platform=self.platform_amazon)
        BrokerPlatform.objects.create(broker=self.broker_two, platform=self.platform_shein)

    def test_filter_brokers_by_category_and_city(self):
        response = self.client.get(
            reverse('filter_brokers'),
            {
                'category': self.category_electronics.id,
                'city': self.city_one.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['brokers']), 1)
        self.assertEqual(payload['brokers'][0]['id'], self.broker_one.id)

    def test_filter_payload_contains_frontend_fields(self):
        response = self.client.get(
            reverse('filter_brokers'),
            {'search': 'Ahmad'},
        )

        self.assertEqual(response.status_code, 200)
        broker = response.json()['brokers'][0]

        self.assertEqual(broker['display_name'], 'Ahmad Saleh')
        self.assertEqual(broker['city'], 'Hebron')
        self.assertEqual(broker['description'], 'Electronics broker')
        self.assertEqual(broker['categories'], ['Electronics'])
        self.assertEqual(broker['avatar_text'], 'A')


class LandingPageBrokerTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='Hebron')
        self.category = Category.objects.create(name='Electronics')
        self.platform = Platform.objects.create(name='Amazon', category=self.category)

    def make_broker(self, username, name, rating, reviews, is_verified=True, is_active=True):
        user = User.objects.create_user(
            username=username,
            password='pass1234',
            role='broker',
            phone='0599000100',
        )
        broker = BrokerProfile.objects.create(
            user=user,
            business_name=name,
            city=self.city,
            whatsapp_number='0599111000',
            average_rating=rating,
            total_reviews=reviews,
            is_verified=is_verified,
            is_active=is_active,
        )
        BrokerPlatform.objects.create(broker=broker, platform=self.platform)
        return broker

    def test_landing_page_shows_top_three_verified_active_brokers_only(self):
        top = self.make_broker('top', 'Top Broker', 5.0, 12)
        second = self.make_broker('second', 'Second Broker', 4.9, 30)
        third = self.make_broker('third', 'Third Broker', 4.8, 8)
        self.make_broker('fourth', 'Fourth Broker', 4.7, 100)
        self.make_broker('unverified', 'Unverified Broker', 5.0, 50, is_verified=False)
        self.make_broker('inactive', 'Inactive Broker', 5.0, 50, is_active=False)

        response = self.client.get(reverse('landing'))

        self.assertEqual(response.status_code, 200)
        brokers = list(response.context['brokers'])
        self.assertEqual(brokers, [top, second, third])
