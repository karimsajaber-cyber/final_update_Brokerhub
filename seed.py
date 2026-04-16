from django.apps import apps
from django.utils import timezone

User = apps.get_model('accounts', 'User')
BrokerProfile = apps.get_model('brokers', 'BrokerProfile')
Platform = apps.get_model('core', 'Platform')
City = apps.get_model('locations', 'City')
QuoteRequest = apps.get_model('requests', 'QuoteRequest')

customer = User.objects.get(username='ahmad_customer')
broker = BrokerProfile.objects.get(user__username='karim_broker')
platform = Platform.objects.first()
city = City.objects.first()

products = [
    'iPhone 15 Pro Max 256GB',
    'Samsung Galaxy S24 Ultra',
    'Sony WH-1000XM5 Headphones',
    'MacBook Air M2 256GB',
]

for name in products:
    QuoteRequest.objects.create(
        product_name=name,
        notes='Please get the best price available.',
        customer=customer,
        broker=broker,
        platform=platform,
        city=city,
        status='pending',
    )

print(f'Done — {QuoteRequest.objects.count()} requests created')