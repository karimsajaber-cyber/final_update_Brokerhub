from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils import timezone
from django.db.models import Avg, Count
from datetime import timedelta
from decimal import Decimal
import os


class Command(BaseCommand):
    help = 'Populate database with full demo data for BrokersHub'

    def handle(self, *args, **options):
        now = timezone.now()

        User           = apps.get_model('accounts',  'User')
        City           = apps.get_model('locations', 'City')
        Category       = apps.get_model('core',      'Category')
        Platform       = apps.get_model('core',      'Platform')
        BrokerProfile  = apps.get_model('brokers',   'BrokerProfile')
        BrokerPlatform = apps.get_model('brokers',   'BrokerPlatform')
        QuoteRequest   = apps.get_model('requests',  'QuoteRequest')
        BrokerQuote    = apps.get_model('requests',  'BrokerQuote')
        Message        = apps.get_model('chat',      'Message')
        Review         = apps.get_model('reviews',   'Review')

        self.stdout.write('\n' + '='*55)
        self.stdout.write('  BrokersHub — Full Database Reset')
        self.stdout.write('='*55 + '\n')

        # ── 0. Clear ──────────────────────────────────────────────────────────
        self.stdout.write('Clearing old data...')
        Review.objects.all().delete()
        Message.objects.all().delete()
        BrokerQuote.objects.all().delete()
        QuoteRequest.objects.all().delete()
        BrokerPlatform.objects.all().delete()
        BrokerProfile.objects.all().delete()
        User.objects.filter(role__in=['broker', 'customer']).delete()
        Platform.objects.all().delete()
        Category.objects.all().delete()
        City.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('  Done\n'))

        # ── 1. Cities ─────────────────────────────────────────────────────────
        cities = {}
        for name in ['Ramallah', 'Jerusalem', 'Nablus', 'Hebron', 'Gaza']:
            cities[name] = City.objects.create(name=name)
        self.stdout.write(self.style.SUCCESS(f'Cities: {len(cities)}\n'))

        # ── 2. Categories + Platforms ─────────────────────────────────────────
        cat_electronics = Category.objects.create(name='Electronics')
        cat_fashion     = Category.objects.create(name='Fashion')
        cat_shopping    = Category.objects.create(name='Shopping')
        cat_home        = Category.objects.create(name='Home & Living')
        cat_sports      = Category.objects.create(name='Sports')

        plat_amazon = Platform.objects.create(name='Amazon', category=cat_electronics)
        plat_shein  = Platform.objects.create(name='Shein',  category=cat_fashion)
        plat_temu   = Platform.objects.create(name='Temu',   category=cat_shopping)

        self.stdout.write(self.style.SUCCESS('Categories: 5 | Platforms: Amazon, Shein, Temu\n'))

        # ── 3. Helper: avatar path ────────────────────────────────────────────
        from django.conf import settings
        def avatar(filename):
            full = os.path.join(settings.MEDIA_ROOT, 'brokers', 'avatars', filename)
            return os.path.join('brokers', 'avatars', filename) if os.path.isfile(full) else None

        # ── 4. Brokers ────────────────────────────────────────────────────────
        self.stdout.write('Creating brokers...')

        def make_broker(username, pwd, first, last, phone, biz, city_key,
                        wa, desc, exp, verified, platform, img_file):
            u = User.objects.create_user(
                username=username, password=pwd,
                email=f'{username}@brokershub.com',
                first_name=first, last_name=last,
                phone=phone, role='broker',
            )
            bp = BrokerProfile.objects.create(
                user=u, business_name=biz, city=cities[city_key],
                whatsapp_number=wa, description=desc,
                experience_years=exp, is_verified=verified, is_active=True,
                average_rating=0, total_reviews=0,
                profile_image=avatar(img_file),
            )
            BrokerPlatform.objects.create(broker=bp, platform=platform)
            self.stdout.write(self.style.SUCCESS(f'  {biz}  ({city_key})'))
            return bp

        broker_qais = make_broker(
            'qais', 'qais123', 'Qais', 'Barakat', '+970591100001',
            'Qais Electronics', 'Ramallah', '0591100001',
            'Electronics specialist with 7 years of experience sourcing from Amazon. '
            'Fast delivery, guaranteed original products, full warranty on every item.',
            7, True, plat_amazon, 'qais_avatar.jpg',
        )
        broker_kareem = make_broker(
            'kareem', 'kareem123', 'Kareem', 'Haddad', '+970591100002',
            'Kareem Fashion Store', 'Jerusalem', '0591100002',
            'Fashion broker specialising in Shein. Expert in sizing, trends, and '
            'curating the best pieces at unbeatable prices. 5 years experience.',
            5, True, plat_shein, 'kareem_avatar.jpg',
        )
        broker_rafeef = make_broker(
            'rafeef', 'rafeef123', 'Rafeef', 'Mansour', '+970591100003',
            'Rafeef Smart Deals', 'Nablus', '0591100003',
            'Your go-to broker for Temu. I source everything from home goods '
            'to accessories at the lowest prices. Reliable and fast.',
            4, False, plat_temu, 'rafeef_avatar.jpg',
        )
        broker_zein = make_broker(
            'zein', 'zein123', 'Zein', 'Saleh', '+970591100004',
            'Zein Premium Imports', 'Hebron', '0591100004',
            'Premium electronics and lifestyle products via Amazon. '
            'I handle everything from order to your doorstep. 6 years in import business.',
            6, True, plat_amazon, 'zein_avatar.jpg',
        )
        self.stdout.write('')

        # ── 5. Main customer — Manar ──────────────────────────────────────────
        self.stdout.write('Creating customer manar...')
        manar = User.objects.create_user(
            username='manar', password='manar123',
            email='manar@example.com',
            first_name='Manar', last_name='Khalil',
            phone='+970598000001', role='customer',
        )
        self.stdout.write(self.style.SUCCESS('  manar / manar123\n'))

        # ── 6. Review customers (secondary, reviews only) ─────────────────────
        self.stdout.write('Creating review customers...')
        review_customers = []
        for uname, first, last in [
            ('lara_k',   'Lara',   'Khoury'),
            ('nour_s',   'Nour',   'Sabbagh'),
            ('sami_h',   'Sami',   'Hamdan'),
            ('hana_a',   'Hana',   'Aqel'),
            ('tariq_m',  'Tariq',  'Musa'),
        ]:
            u = User.objects.create_user(
                username=uname, password='pass123',
                email=f'{uname}@example.com',
                first_name=first, last_name=last,
                phone='+97059900000', role='customer',
            )
            review_customers.append(u)
            self.stdout.write(self.style.SUCCESS(f'  {uname}'))
        lara, nour, sami, hana, tariq = review_customers
        self.stdout.write('')

        # ── 7. Manar's requests with Qais (4 pending) ─────────────────────────
        self.stdout.write("Manar's requests with Qais (pending)...")
        pending_items = [
            ('iPhone 15 Pro 256GB — Natural Titanium',
             'Need the natural titanium colour with original Apple warranty. EU version preferred.',
             'https://www.amazon.com/dp/B0CHX2FBZQ'),
            ('Samsung Galaxy S24 Ultra 512GB',
             'Black colour, 512GB storage. Must include official Samsung warranty.',
             'https://www.amazon.com/dp/B0CMDWC436'),
            ('Sony WH-1000XM5 Noise Cancelling Headphones',
             'Black version with carrying case. Need proof of authenticity.',
             'https://www.amazon.com/dp/B09XS7JWHH'),
            ('DJI Mini 4 Pro Drone',
             'Standard combo if possible. Looking for best price with fly-more kit.',
             'https://www.amazon.com/dp/B0CG8M6WR8'),
        ]
        for i, (name, notes, url) in enumerate(pending_items):
            r = QuoteRequest.objects.create(
                product_name=name, notes=notes, product_url=url,
                customer=manar, broker=broker_qais,
                platform=plat_amazon, city=cities['Ramallah'],
                status='pending',
            )
            QuoteRequest.objects.filter(pk=r.pk).update(
                created_at=now - timedelta(days=i+1),
                updated_at=now - timedelta(days=i+1),
            )
            self.stdout.write(self.style.SUCCESS(f'  [PENDING] {name[:50]}'))
        self.stdout.write('')

        # ── 8. Manar's other requests (various statuses) ──────────────────────
        self.stdout.write("Manar's other requests...")

        def make_req(name, notes, customer, broker, platform, city_key, status, days_ago):
            r = QuoteRequest.objects.create(
                product_name=name, notes=notes,
                customer=customer, broker=broker,
                platform=platform, city=cities[city_key],
                status=status,
            )
            QuoteRequest.objects.filter(pk=r.pk).update(
                created_at=now - timedelta(days=days_ago),
                updated_at=now - timedelta(days=max(0, days_ago-2)),
            )
            r.refresh_from_db()
            return r

        req_quoted = make_req(
            'Shein Winter Jacket + 3 Tops Bundle',
            'Size M for jacket, S for tops. Neutral colours preferred.',
            manar, broker_kareem, plat_shein, 'Jerusalem', 'quoted', 5,
        )
        q_quoted = BrokerQuote.objects.create(
            quote_request=req_quoted, broker=broker_kareem,
            total_price=Decimal('68.00'), delivery_days=14,
            notes='Winter jacket size M + 3 tops size S. Neutral tones.', status='sent',
        )

        req_accepted = make_req(
            'Temu Kitchen Storage Set (12 pieces)',
            'White or transparent plastic. Stackable preferred.',
            manar, broker_rafeef, plat_temu, 'Nablus', 'accepted', 8,
        )
        q_accepted = BrokerQuote.objects.create(
            quote_request=req_accepted, broker=broker_rafeef,
            total_price=Decimal('42.00'), delivery_days=16,
            notes='12-piece kitchen storage, white stackable set.', status='accepted',
        )

        req_completed = make_req(
            'Apple AirPods Pro 2nd Gen (MagSafe)',
            'White, with MagSafe charging case. Original Apple.',
            manar, broker_zein, plat_amazon, 'Hebron', 'completed', 18,
        )
        q_completed = BrokerQuote.objects.create(
            quote_request=req_completed, broker=broker_zein,
            total_price=Decimal('195.00'), delivery_days=7,
            notes='AirPods Pro 2, sealed box, Apple warranty.', status='accepted',
        )

        req_cancelled = make_req(
            'Samsung Galaxy Tab S9 Ultra',
            'Wi-Fi only, 256GB, graphite colour.',
            manar, broker_qais, plat_amazon, 'Ramallah', 'cancelled', 12,
        )
        BrokerQuote.objects.create(
            quote_request=req_cancelled, broker=broker_qais,
            total_price=Decimal('799.00'), delivery_days=10,
            notes='Tab S9 Ultra Wi-Fi 256GB graphite.', status='rejected',
        )

        for s, name in [('QUOTED','Shein Bundle'),('ACCEPTED','Temu Kitchen Set'),
                        ('COMPLETED','AirPods Pro'),('CANCELLED','Galaxy Tab')]:
            self.stdout.write(self.style.SUCCESS(f'  [{s:10}] {name}'))
        self.stdout.write('')

        # ── 9. Chat messages — Manar & Qais (pending request 1) ───────────────
        self.stdout.write('Creating chat messages...')
        qais_user = broker_qais.user

        iphone_req = QuoteRequest.objects.filter(
            customer=manar, broker=broker_qais, status='pending'
        ).order_by('created_at').first()

        if iphone_req:
            def msg(req, sender, receiver, text, days_back, mins_back):
                m = Message.objects.create(
                    quote_request=req, sender=sender,
                    receiver=receiver, text=text, is_read=True,
                )
                Message.objects.filter(pk=m.pk).update(
                    created_at=now - timedelta(days=days_back, minutes=mins_back)
                )

            msg(iphone_req, manar,     qais_user, 'Hi Qais! I need the iPhone 15 Pro 256GB in natural titanium. Can you source it from Amazon?',                 1, 60)
            msg(iphone_req, qais_user, manar,     'Hello Manar! Yes absolutely. I can get the iPhone 15 Pro 256GB Natural Titanium — EU version with Apple warranty.',  1, 55)
            msg(iphone_req, manar,     qais_user, 'Great! What would be the total price including delivery to Ramallah?',                                        1, 50)
            msg(iphone_req, qais_user, manar,     'All-in price would be $1,089 with delivery in 7 days. Includes Apple warranty and sealed box guarantee.',     1, 45)
            msg(iphone_req, manar,     qais_user, 'That sounds reasonable. Let me think about it and I will get back to you soon.',                              1, 40)
            msg(iphone_req, qais_user, manar,     'Of course, no rush! Feel free to ask any questions. I am always available.',                                  1, 35)
            self.stdout.write(self.style.SUCCESS('  iPhone request: 6 messages'))

        # Manar & Kareem (quoted)
        kareem_user = broker_kareem.user
        msg(req_quoted, manar,       kareem_user, 'Hi Kareem! I need a winter jacket size M and 3 tops size S from Shein.',        5, 90)
        msg(req_quoted, kareem_user, manar,       'Hi Manar! Perfect, that is my specialty. Any colour preference for the jacket?', 5, 85)
        msg(req_quoted, manar,       kareem_user, 'Neutral colours — beige, grey, or black. Nothing too bright please.',            5, 80)
        msg(req_quoted, kareem_user, manar,       'Got it. I will put together the best options. Sent you a quote for $68 total.', 5, 75)
        self.stdout.write(self.style.SUCCESS('  Shein bundle: 4 messages'))
        self.stdout.write('')

        # ── 10. Reviews from secondary customers ──────────────────────────────
        self.stdout.write('Creating reviews...')

        def make_review_set(customer, broker, platform, city_key, product, price, days_ago, rating, comment):
            req = QuoteRequest.objects.create(
                product_name=product, notes=f'Order: {product}',
                customer=customer, broker=broker,
                platform=platform, city=cities[city_key], status='completed',
            )
            QuoteRequest.objects.filter(pk=req.pk).update(
                created_at=now - timedelta(days=days_ago+7),
                updated_at=now - timedelta(days=days_ago),
            )
            req.refresh_from_db()
            q = BrokerQuote.objects.create(
                quote_request=req, broker=broker,
                total_price=Decimal(str(price)), delivery_days=7,
                status='accepted',
            )
            Review.objects.create(
                customer=customer, broker=broker, broker_quote=q,
                rating=rating, comment=comment,
            )

        # Qais reviews (3)
        make_review_set(lara,  broker_qais, plat_amazon, 'Ramallah',
            'MacBook Air M2 256GB', 1149, 20, 5,
            'Qais is hands down the best electronics broker! My MacBook arrived sealed and in perfect condition in just 7 days. He was responsive, professional, and gave me the best price I found anywhere. Highly recommend!')
        make_review_set(nour,  broker_qais, plat_amazon, 'Jerusalem',
            'Apple Watch Series 9 45mm', 389, 35, 5,
            'Exceptional service from start to finish. The Apple Watch is 100% original with full warranty. Qais kept me updated throughout and delivered ahead of schedule. Will definitely order again.')
        make_review_set(sami,  broker_qais, plat_amazon, 'Nablus',
            'Samsung Galaxy S24 256GB', 799, 50, 4,
            'Very good experience. The Samsung arrived sealed and authentic. Delivery was a day late but Qais communicated well and offered a small discount. Reliable broker, will use again.')

        # Kareem reviews (3)
        make_review_set(hana,  broker_kareem, plat_shein, 'Jerusalem',
            'Shein Summer Collection — 6 Dresses', 92, 15, 5,
            'Kareem is incredible at what he does! He picked the most beautiful dresses and everything fit perfectly. The quality was better than expected for the price. Will be ordering every season!')
        make_review_set(tariq, broker_kareem, plat_shein, 'Ramallah',
            'Shein Men Casual Wear Bundle', 65, 30, 4,
            'Good experience overall. Kareem is knowledgeable about Shein sizing and helped me pick the right sizes. Delivery took 16 days but everything arrived in great condition.')
        make_review_set(lara,  broker_kareem, plat_shein, 'Hebron',
            'Shein Kids Back-to-School Bundle', 55, 45, 5,
            'Amazing service! Kareem put together a perfect back-to-school bundle for my kids. Sizes were spot on and the quality was great. Communication was smooth and fast. 5 stars!')

        # Rafeef reviews (3)
        make_review_set(nour,  broker_rafeef, plat_temu, 'Nablus',
            'Temu Home Organizer Set — 15 pieces', 38, 10, 4,
            'Solid experience with Rafeef. The organizer set is sturdy and good quality for the price. She responded quickly and kept me informed. Delivery was on time. Would recommend for Temu orders.')
        make_review_set(sami,  broker_rafeef, plat_temu, 'Gaza',
            'Temu Sports Accessories Bundle', 47, 25, 5,
            'Really impressed! Rafeef is professional and reliable. The sports bundle arrived well-packaged and everything was exactly as ordered. Best Temu broker I have used. Will order again soon.')
        make_review_set(hana,  broker_rafeef, plat_temu, 'Ramallah',
            'Temu Kitchen Gadgets Set', 42, 40, 4,
            'Good experience. Rafeef handled the order efficiently and the kitchen gadgets are great quality for the price. Minor delay but she communicated proactively. Trustworthy broker.')

        # Zein reviews (3)
        make_review_set(tariq, broker_zein, plat_amazon, 'Hebron',
            'Sony PlayStation 5 Disc Edition', 520, 14, 5,
            'Outstanding! Zein sourced the PS5 at an excellent price and it arrived sealed with full warranty. Fast communication, professional service, and delivery was right on schedule. Top-tier broker!')
        make_review_set(lara,  broker_zein, plat_amazon, 'Jerusalem',
            'iPad Pro 12.9" M2 256GB', 899, 28, 5,
            'Zein is exceptional. The iPad arrived in perfect condition, sealed box with Apple warranty. He answered all my questions patiently and the price was the best I found. Highly recommend.')
        make_review_set(nour,  broker_zein, plat_amazon, 'Ramallah',
            'Dyson V15 Detect Vacuum', 649, 42, 4,
            'Great service from Zein. The Dyson arrived authentic and in perfect working condition. Delivery was professional and well-packaged. Price was fair. Will use again for future purchases.')

        # Also create review for Manar's completed request (Zein / AirPods)
        Review.objects.create(
            customer=manar, broker=broker_zein, broker_quote=q_completed,
            rating=5,
            comment='Zein delivered my AirPods Pro perfectly! Sealed box, MagSafe case included, and arrived in only 7 days. Price was great and communication was excellent throughout. Highly recommend!',
        )

        # Update all broker ratings
        for bp in [broker_qais, broker_kareem, broker_rafeef, broker_zein]:
            agg = Review.objects.filter(broker=bp).aggregate(avg=Avg('rating'), cnt=Count('id'))
            if agg['avg']:
                BrokerProfile.objects.filter(pk=bp.pk).update(
                    average_rating=round(agg['avg'], 1),
                    total_reviews=agg['cnt'],
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  {bp.business_name}: {round(agg["avg"],1)}★ ({agg["cnt"]} reviews)'
                ))
        self.stdout.write('')

        # ── 11. Admin ─────────────────────────────────────────────────────────
        self.stdout.write('Admin superuser...')
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin', email='admin@brokershub.com',
                password='admin123', role='admin', phone='+970500000000',
            )
        self.stdout.write(self.style.SUCCESS('  admin / admin123\n'))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('='*55)
        self.stdout.write(self.style.SUCCESS('  ALL DONE!'))
        self.stdout.write('='*55 + '\n')

        self.stdout.write('CREDENTIALS')
        self.stdout.write('-'*42)
        self.stdout.write('Broker  | qais     | qais123')
        self.stdout.write('Broker  | kareem   | kareem123')
        self.stdout.write('Broker  | rafeef   | rafeef123')
        self.stdout.write('Broker  | zein     | zein123')
        self.stdout.write('Customer| manar    | manar123')
        self.stdout.write('Admin   | admin    | admin123')
        self.stdout.write('-'*42 + '\n')

        self.stdout.write('COUNTS')
        self.stdout.write(f'  Brokers  : {BrokerProfile.objects.count()}')
        self.stdout.write(f'  Customers: {User.objects.filter(role="customer").count()}')
        self.stdout.write(f'  Requests : {QuoteRequest.objects.count()}')
        self.stdout.write(f'  Quotes   : {BrokerQuote.objects.count()}')
        self.stdout.write(f'  Messages : {Message.objects.count()}')
        self.stdout.write(f'  Reviews  : {Review.objects.count()}')
        self.stdout.write('')
