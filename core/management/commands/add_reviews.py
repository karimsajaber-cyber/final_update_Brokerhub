from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils import timezone
from django.db.models import Avg, Count
from datetime import timedelta
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Add realistic reviews for all brokers (safe — does not delete existing data)'

    def handle(self, *args, **options):
        now = timezone.now()

        User           = apps.get_model('accounts',  'User')
        City           = apps.get_model('locations', 'City')
        Platform       = apps.get_model('core',      'Platform')
        BrokerProfile  = apps.get_model('brokers',   'BrokerProfile')
        QuoteRequest   = apps.get_model('requests',  'QuoteRequest')
        BrokerQuote    = apps.get_model('requests',  'BrokerQuote')
        Review         = apps.get_model('reviews',   'Review')

        self.stdout.write('\n' + '='*55)
        self.stdout.write('  Adding Reviews to All Brokers')
        self.stdout.write('='*55 + '\n')

        # Get existing data
        try:
            customer = User.objects.get(username='ahmad_customer')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('ahmad_customer not found. Run populate_db first.'))
            return

        brokers = BrokerProfile.objects.select_related('user').all()
        if not brokers.exists():
            self.stdout.write(self.style.ERROR('No brokers found. Run populate_db first.'))
            return

        platform = Platform.objects.first()
        city     = City.objects.first()

        if not platform or not city:
            self.stdout.write(self.style.ERROR('No platforms or cities found. Run populate_db first.'))
            return

        # ── Review data per broker ────────────────────────────────────────────
        reviews_data = {
            'karim_broker': [
                {
                    'product' : 'iPhone 15 Pro Max 256GB — Black Titanium',
                    'price'   : '1089.00',
                    'days'    : 7,
                    'days_ago': 8,
                    'rating'  : 5,
                    'comment' : 'Karim delivered the iPhone exactly as described — sealed box, original Apple warranty. Arrived in 7 days to Ramallah. Exceptional service, very transparent and responsive throughout the process. Will definitely order again!',
                },
                {
                    'product' : 'MacBook Air M2 — Space Grey 256GB',
                    'price'   : '1149.00',
                    'days'    : 10,
                    'days_ago': 22,
                    'rating'  : 5,
                    'comment' : 'Outstanding experience! The MacBook arrived perfectly packaged and in flawless condition. Karim kept me updated at every step and the price was the best I found anywhere. Highly professional broker.',
                },
                {
                    'product' : 'Sony PlayStation 5 — Disc Edition',
                    'price'   : '520.00',
                    'days'    : 9,
                    'days_ago': 35,
                    'rating'  : 5,
                    'comment' : 'Excellent! PS5 arrived sealed and authentic. Karim handled everything smoothly — from order to delivery. Great communication and fair pricing. My go-to broker for electronics.',
                },
                {
                    'product' : 'Samsung 65" QLED 4K Smart TV',
                    'price'   : '899.00',
                    'days'    : 8,
                    'days_ago': 50,
                    'rating'  : 4,
                    'comment' : 'Good experience overall. The Samsung TV arrived in perfect condition and the price was competitive. Delivery took a day longer than estimated but Karim communicated proactively. Solid broker.',
                },
                {
                    'product' : 'Apple AirPods Pro 2nd Gen — MagSafe',
                    'price'   : '195.00',
                    'days'    : 6,
                    'days_ago': 60,
                    'rating'  : 5,
                    'comment' : 'Smooth and fast. AirPods Pro arrived in 6 days, original with Apple warranty card. Karim is honest, prices are fair, and he replies quickly. 5 stars without hesitation.',
                },
            ],
            'sara_broker': [
                {
                    'product' : 'Shein Summer Collection — 5 Dresses (S/M)',
                    'price'   : '85.00',
                    'days'    : 14,
                    'days_ago': 10,
                    'rating'  : 5,
                    'comment' : 'Sara curated the most beautiful selection for me! 5 pastel dresses, all true to size. She was patient, detailed, and the delivery was on time. The quality exceeded my expectations for the price.',
                },
                {
                    'product' : 'ASOS Premium Blazer Set — Women',
                    'price'   : '72.00',
                    'days'    : 12,
                    'days_ago': 28,
                    'rating'  : 5,
                    'comment' : 'Sara knows fashion! The blazer set arrived beautifully packaged. She helped me choose the right size and even sent photos before shipping. Incredible attention to detail. Will be ordering again soon.',
                },
                {
                    'product' : 'Shein Kids Back-to-School Bundle',
                    'price'   : '55.00',
                    'days'    : 16,
                    'days_ago': 45,
                    'rating'  : 4,
                    'comment' : 'Great service! Sara put together a lovely back-to-school bundle for my kids. Everything fits well and the prices are unbeatable. Delivery was slightly delayed due to customs but Sara handled it professionally.',
                },
                {
                    'product' : 'Shein Loungewear Set — 3 Pieces',
                    'price'   : '38.00',
                    'days'    : 13,
                    'days_ago': 70,
                    'rating'  : 5,
                    'comment' : 'Perfect experience from start to finish. Sara is knowledgeable, responsive, and genuinely cares about the customer. The loungewear is soft, stylish, and exactly what I ordered. 5 stars!',
                },
            ],
            'omar_broker': [
                {
                    'product' : 'Temu Home Storage Set — 10 Pieces',
                    'price'   : '45.00',
                    'days'    : 18,
                    'days_ago': 12,
                    'rating'  : 4,
                    'comment' : 'Omar delivered exactly what was ordered. The storage set is sturdy and well-made for the price. Communication was good and he followed up after delivery. A reliable broker for everyday items.',
                },
                {
                    'product' : 'Temu Kitchen Organizer Bundle',
                    'price'   : '38.00',
                    'days'    : 20,
                    'days_ago': 30,
                    'rating'  : 4,
                    'comment' : 'Good experience! The kitchen organizers are exactly as shown and the price through Omar was better than any local option. Delivery took a little longer but the quality was worth the wait.',
                },
                {
                    'product' : 'Temu Sports Bag + Accessories Set',
                    'price'   : '52.00',
                    'days'    : 15,
                    'days_ago': 55,
                    'rating'  : 5,
                    'comment' : 'Really happy with this order! Omar handled everything professionally. The sports bag is high quality, very spacious, and arrived well-packaged. Great value and reliable service.',
                },
            ],
        }

        total_created = 0

        for username, review_list in reviews_data.items():
            try:
                broker = BrokerProfile.objects.get(user__username=username)
            except BrokerProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  Broker {username} not found, skipping.'))
                continue

            self.stdout.write(f'\n  {broker.business_name}:')

            for rv in review_list:
                # Create completed QuoteRequest
                req = QuoteRequest.objects.create(
                    product_name = rv['product'],
                    notes        = f'Completed order — {rv["product"]}',
                    customer     = customer,
                    broker       = broker,
                    platform     = platform,
                    city         = city,
                    status       = 'completed',
                )
                QuoteRequest.objects.filter(pk=req.pk).update(
                    created_at = now - timedelta(days=rv['days_ago'] + rv['days']),
                    updated_at = now - timedelta(days=rv['days_ago']),
                )

                # Create BrokerQuote
                quote = BrokerQuote.objects.create(
                    quote_request = req,
                    broker        = broker,
                    total_price   = Decimal(rv['price']),
                    delivery_days = rv['days'],
                    status        = 'accepted',
                    notes         = f'Delivered in {rv["days"]} days.',
                )

                # Create Review
                Review.objects.create(
                    customer     = customer,
                    broker       = broker,
                    broker_quote = quote,
                    rating       = rv['rating'],
                    comment      = rv['comment'],
                )

                stars = '★' * rv['rating'] + '☆' * (5 - rv['rating'])
                self.stdout.write(self.style.SUCCESS(
                    f'    {stars}  {rv["product"][:45]}'
                ))
                total_created += 1

            # Update broker rating from real reviews
            agg = Review.objects.filter(broker=broker).aggregate(
                avg=Avg('rating'), cnt=Count('id')
            )
            BrokerProfile.objects.filter(pk=broker.pk).update(
                average_rating = round(agg['avg'], 1),
                total_reviews  = agg['cnt'],
            )
            self.stdout.write(f'    → Rating updated: {round(agg["avg"],1)}/5  ({agg["cnt"]} reviews)')

        self.stdout.write('\n' + '='*55)
        self.stdout.write(self.style.SUCCESS(f'  Done — {total_created} reviews created'))
        self.stdout.write('='*55 + '\n')
