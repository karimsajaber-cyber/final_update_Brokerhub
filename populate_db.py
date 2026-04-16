"""
BrokersHub — Database Population Script
=======================================
Run with:
    python manage.py shell < populate_db.py

NOTE: Uses apps.get_model() to avoid conflict with the
      'requests' Python library vs the 'requests' Django app.
"""

import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BrokersHub.settings')

from django.apps import apps
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

# ── Safe model imports (avoids requests lib conflict) ─────────────────────────
User          = apps.get_model('accounts',  'User')
City          = apps.get_model('locations', 'City')
Category      = apps.get_model('core',      'Category')
Platform      = apps.get_model('core',      'Platform')
BrokerProfile = apps.get_model('brokers',   'BrokerProfile')
BrokerPlatform= apps.get_model('brokers',   'BrokerPlatform')
QuoteRequest  = apps.get_model('requests',  'QuoteRequest')
BrokerQuote   = apps.get_model('requests',  'BrokerQuote')
Message       = apps.get_model('chat',      'Message')
Review        = apps.get_model('reviews',   'Review')

print("\n" + "="*55)
print("  BrokersHub — Database Population Script")
print("="*55 + "\n")

# ── 0. Clean slate ────────────────────────────────────────────────────────────
print("🗑️  Clearing old data...")
Review.objects.all().delete()
Message.objects.all().delete()
BrokerQuote.objects.all().delete()
QuoteRequest.objects.all().delete()
BrokerPlatform.objects.all().delete()
BrokerProfile.objects.all().delete()
User.objects.filter(is_superuser=False).delete()
Platform.objects.all().delete()
Category.objects.all().delete()
City.objects.all().delete()
print("   ✓ Done\n")

now = timezone.now()

# ── 1. Cities ─────────────────────────────────────────────────────────────────
print("🌍 Cities...")
city_names = ["Ramallah", "Jerusalem", "Nablus", "Hebron", "Gaza"]
cities = {n: City.objects.create(name=n) for n in city_names}
print(f"   ✓ {len(cities)} cities\n")

# ── 2. Categories + Platforms ─────────────────────────────────────────────────
print("🗂️  Categories & Platforms...")
cat_map = {
    "Electronics" : ["Amazon", "Noon"],
    "Fashion"     : ["Shein", "ASOS"],
    "Shopping"    : ["Temu", "eBay"],
    "Home & Living": ["IKEA Online", "Wayfair"],
    "Sports"      : ["Nike", "Adidas"],
}
cats = {}
plats = {}
for cat_name, plat_list in cat_map.items():
    cat = Category.objects.create(name=cat_name)
    cats[cat_name] = cat
    for p in plat_list:
        plats[p] = Platform.objects.create(name=p, category=cat)
print(f"   ✓ {len(cats)} categories, {len(plats)} platforms\n")

# ── 3. Broker Users + Profiles ────────────────────────────────────────────────
print("👔 Brokers...")

def make_broker(username, email, first, last, phone,
                biz_name, city_key, whatsapp, desc,
                exp, verified, rating, reviews_count, plat_keys):
    u = User.objects.create_user(
        username=username, email=email, password="broker123!",
        first_name=first, last_name=last, phone=phone, role="broker",
    )
    bp = BrokerProfile.objects.create(
        user=u, business_name=biz_name, city=cities[city_key],
        whatsapp_number=whatsapp, description=desc,
        experience_years=exp, is_verified=verified, is_active=True,
        average_rating=rating, total_reviews=reviews_count,
    )
    for pk in plat_keys:
        BrokerPlatform.objects.create(broker=bp, platform=plats[pk])
    print(f"   ✓ {biz_name} — {city_key} — ⭐{rating}")
    return bp

broker_k = make_broker(
    "karim_broker","karim@brokershub.com","Karim","Mansour","+970591234567",
    "Karim Tech Imports","Ramallah","0591234567",
    "Electronics & gadgets specialist. 8 years of import experience. Fast delivery, competitive prices.",
    8, True, 4.8, 24, ["Amazon","Noon"],
)
broker_s = make_broker(
    "sara_broker","sara@brokershub.com","Sara","Al-Ahmad","+970597654321",
    "Sara Fashion Hub","Jerusalem","0597654321",
    "Fashion & lifestyle broker. Shein and ASOS at the best rates. 5 years of experience.",
    5, True, 4.5, 17, ["Shein","ASOS"],
)
broker_o = make_broker(
    "omar_broker","omar@brokershub.com","Omar","Khalil","+970599112233",
    "Omar General Trading","Nablus","0599112233",
    "General merchandise — sports, home & everyday products. Reliable and affordable.",
    3, False, 4.1, 9, ["Temu","Nike","IKEA Online"],
)
print()

# ── 4. Customer ───────────────────────────────────────────────────────────────
print("👤 Customer...")
customer = User.objects.create_user(
    username="ahmad_customer", email="ahmad@example.com", password="customer123!",
    first_name="Ahmad", last_name="Nasser", phone="+970598765432", role="customer",
)
print(f"   ✓ ahmad_customer\n")

# ── 5. Quote Requests (one per status) ───────────────────────────────────────
print("📋 Quote Requests...")

def make_req(name, notes, url, broker, plat_key, city_key, status, days_ago):
    r = QuoteRequest.objects.create(
        product_name=name, notes=notes, product_url=url,
        customer=customer, broker=broker,
        platform=plats[plat_key], city=cities[city_key], status=status,
    )
    QuoteRequest.objects.filter(pk=r.pk).update(
        created_at=now - timedelta(days=days_ago),
        updated_at=now - timedelta(days=max(0, days_ago - 2)),
    )
    r.refresh_from_db()
    print(f"   ✓ [{status.upper():10}] {name[:45]}")
    return r

req_pending = make_req(
    "iPhone 15 Pro Max 256GB",
    "Black titanium version. Must be original with full warranty.",
    "https://www.amazon.com/dp/B0CHX1W1XY",
    broker_k, "Amazon", "Ramallah", "pending", 1,
)
req_quoted = make_req(
    "Nike Air Max 270 (EU Size 43)",
    "White and black colorway. Need within 2 weeks.",
    "https://www.nike.com/t/air-max-270",
    broker_o, "Nike", "Nablus", "quoted", 4,
)
req_accepted = make_req(
    "Samsung 65\" QLED 4K TV",
    "Model QN65Q80C or similar. Looking for the best price.",
    "https://www.amazon.com/dp/B0BZ3BKBK9",
    broker_k, "Amazon", "Ramallah", "accepted", 10,
)
req_completed = make_req(
    "Shein Summer Dress Collection (5 pieces)",
    "Mixed S and M sizes, pastel colours preferred.",
    "https://www.shein.com",
    broker_s, "Shein", "Jerusalem", "completed", 20,
)
req_cancelled = make_req(
    "IKEA KALLAX Shelf 4x4 White",
    "147x147cm, white. Delivery to Hebron.",
    "https://www.ikea.com/us/en/p/kallax-shelf-unit-white-20275861/",
    broker_o, "IKEA Online", "Hebron", "cancelled", 15,
)
print()

# ── 6. Broker Quotes ──────────────────────────────────────────────────────────
print("💰 Broker Quotes...")

q_quoted = BrokerQuote.objects.create(
    quote_request=req_quoted, broker=broker_o,
    total_price=Decimal("135.00"), delivery_days=12,
    notes="Price includes shipping. Nike original with box.", status="sent",
)
q_accepted = BrokerQuote.objects.create(
    quote_request=req_accepted, broker=broker_k,
    total_price=Decimal("899.00"), delivery_days=7,
    notes="Samsung QN65Q80C sealed box. Free delivery to Ramallah.", status="accepted",
)
q_completed = BrokerQuote.objects.create(
    quote_request=req_completed, broker=broker_s,
    total_price=Decimal("85.00"), delivery_days=14,
    notes="5 pastel dresses S/M. Already shipped.", status="accepted",
)
q_cancelled = BrokerQuote.objects.create(
    quote_request=req_cancelled, broker=broker_o,
    total_price=Decimal("210.00"), delivery_days=21,
    notes="KALLAX 4x4 white, delivery to Hebron included.", status="rejected",
)
print("   ✓ 4 quotes created\n")

# ── 7. Reviews ────────────────────────────────────────────────────────────────
print("⭐ Reviews...")
Review.objects.create(
    customer=customer, broker=broker_s, broker_quote=q_completed,
    rating=5,
    comment="Sara was amazing! The dresses arrived exactly as described. Great quality. Will use again! 🌟",
)
print("   ✓ 1 review created\n")

# ── 8. Chat Messages ──────────────────────────────────────────────────────────
print("💬 Chat Messages...")

def msg(req, sender, receiver, text, days_back, mins_back):
    m = Message.objects.create(
        quote_request=req, sender=sender, receiver=receiver,
        text=text, is_read=True,
    )
    Message.objects.filter(pk=m.pk).update(
        created_at=now - timedelta(days=days_back, minutes=mins_back)
    )

ku = broker_k.user
su = broker_s.user
ou = broker_o.user
c  = customer

# Karim & Ahmad — Samsung TV (accepted)
msg(req_accepted, c,  ku, "Hi Karim! I'm interested in the Samsung 65\" QLED TV. Can you get it?",                      9, 60)
msg(req_accepted, ku, c,  "Hello Ahmad! Yes, I can source the QN65Q80C. Are you flexible on the exact model?",          9, 55)
msg(req_accepted, c,  ku, "Flexible as long as it's a 65\" QLED 4K Samsung from 2023 or newer. Best price?",            9, 50)
msg(req_accepted, ku, c,  "I can get it for $899 all-in — shipping + delivery to Ramallah. 7 days.",                    9, 45)
msg(req_accepted, c,  ku, "That sounds fair. Accepted! When can you start the order?",                                  9, 40)
msg(req_accepted, ku, c,  "Perfect! Placing the order today. Tracking details within 48 hours 📦",                      9, 35)
msg(req_accepted, c,  ku, "Awesome, thank you!",                                                                        9, 30)
msg(req_accepted, ku, c,  "Order placed ✅ Tracking number coming soon. Message me anytime.",                           9, 20)
print("   ✓ Samsung TV: 8 messages")

# Sara & Ahmad — Shein dresses (completed)
msg(req_completed, c,  su, "Hi Sara! I need 5 Shein dresses — S and M sizes, pastel colours. Can you help?",           19, 90)
msg(req_completed, su, c,  "Hi Ahmad! Of course 😊 Shein is my specialty. Should I curate a selection for you?",       19, 85)
msg(req_completed, c,  su, "Yes please! Budget around $80-90 for the 5 pieces.",                                       19, 80)
msg(req_completed, su, c,  "Perfect budget! Give me 24h to prepare the best picks in pastels.",                        19, 75)
msg(req_completed, su, c,  "Here: 2 midi dresses (sage green + lavender) + 3 casual dresses. Total: $85. Deal?",       19, 48)
msg(req_completed, c,  su, "Yes! Love the selection. Quote accepted ✓",                                                19, 44)
msg(req_completed, su, c,  "Great! Order placed. 14 days delivery. I'll keep you updated 🛍️",                         19, 40)
msg(req_completed, c,  su, "Thank you Sara! Really appreciate how smooth this was.",                                   19, 10)
msg(req_completed, su, c,  "Dresses shipped to you — tracking: SH-847291 ✈️",                                          19,  5)
msg(req_completed, c,  su, "Received! Everything is perfect ⭐⭐⭐⭐⭐",                                                 19,  2)
print("   ✓ Shein dresses: 10 messages")

# Omar & Ahmad — Nike shoes (quoted)
msg(req_quoted, c,  ou, "Hi Omar! Nike Air Max 270 size 43, white/black. What's your price?",                           3, 30)
msg(req_quoted, ou, c,  "Hello! I can get those for $135 including delivery — about 12 days. Interested?",              3, 25)
msg(req_quoted, c,  ou, "Hmm, is there room to negotiate?",                                                             3, 20)
msg(req_quoted, ou, c,  "I can do $128 if you decide today — that's my best offer, shipping included.",                 3, 15)
print("   ✓ Nike shoes: 4 messages\n")

# ── 9. Admin Superuser ────────────────────────────────────────────────────────
print("🔑 Admin superuser...")
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(
        username="admin", email="admin@brokershub.com",
        password="admin123!", role="admin", phone="+970500000000",
    )
    print("   ✓ admin created")
else:
    print("   ℹ️  admin already exists")

print()
print("="*55)
print("✅  ALL DONE!")
print("="*55)
print()
print("CREDENTIALS")
print("-"*40)
print("Broker 1  | karim_broker   | broker123!")
print("Broker 2  | sara_broker    | broker123!")
print("Broker 3  | omar_broker    | broker123!")
print("Customer  | ahmad_customer | customer123!")
print("Admin     | admin          | admin123!")
print("-"*40)
print()
print("COUNTS")
print(f"  Cities    : {City.objects.count()}")
print(f"  Categories: {Category.objects.count()}")
print(f"  Platforms : {Platform.objects.count()}")
print(f"  Brokers   : {BrokerProfile.objects.count()}")
print(f"  Requests  : {QuoteRequest.objects.count()}")
print(f"  Quotes    : {BrokerQuote.objects.count()}")
print(f"  Messages  : {Message.objects.count()}")
print(f"  Reviews   : {Review.objects.count()}")
print()
