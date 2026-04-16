import re
from decimal import Decimal, InvalidOperation

from django.db import models
from accounts.models import User
from locations.models import City
from core.models import Platform
from brokers.models import BrokerProfile



class QuoteRequest(models.Model):
    PRICE_PATTERN = re.compile(r'\[Price:\s*\$?(?P<price>\d+(?:\.\d+)?)\]')
    DELIVERY_PATTERN = re.compile(r'\[Delivery:\s*(?P<days>\d+)\s*days?\]')

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('quoted', 'Quoted'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    customer = models.ForeignKey(User, on_delete=models.CASCADE)

    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)

    product_name = models.CharField(max_length=255)

    product_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    broker = models.ForeignKey(BrokerProfile, on_delete=models.CASCADE,null=True)   
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product_name} - {self.customer.username}"

    def extract_suggested_price(self):
        if not self.notes:
            return None

        match = self.PRICE_PATTERN.search(self.notes)
        if not match:
            return None

        try:
            return Decimal(match.group('price'))
        except (InvalidOperation, TypeError):
            return None

    def extract_suggested_delivery_days(self):
        if not self.notes:
            return None

        match = self.DELIVERY_PATTERN.search(self.notes)
        if not match:
            return None

        try:
            return int(match.group('days'))
        except (TypeError, ValueError):
            return None

    def get_assigned_quote(self):
        if not self.broker_id:
            return None
        return BrokerQuote.objects.filter(
            quote_request=self,
            broker_id=self.broker_id,
        ).first()

    def sync_assigned_quote_from_request_metadata(self):
        if not self.broker_id:
            return None

        broker_quote = self.get_assigned_quote()
        suggested_price = self.extract_suggested_price()
        suggested_delivery_days = self.extract_suggested_delivery_days()

        if broker_quote is None and suggested_price and suggested_price > 0:
            return BrokerQuote.objects.create(
                quote_request=self,
                broker_id=self.broker_id,
                total_price=suggested_price,
                delivery_days=suggested_delivery_days or 1,
                status='accepted' if self.status in {'accepted', 'completed'} else 'sent',
                notes='Recovered from request metadata',
            )

        if broker_quote is None:
            return None

        changed = False

        if broker_quote.total_price <= 0 and suggested_price and suggested_price > 0:
            broker_quote.total_price = suggested_price
            changed = True

        if broker_quote.delivery_days <= 0 and suggested_delivery_days and suggested_delivery_days > 0:
            broker_quote.delivery_days = suggested_delivery_days
            changed = True

        if self.status in {'accepted', 'completed'} and broker_quote.status != 'accepted':
            broker_quote.status = 'accepted'
            changed = True

        if changed:
            broker_quote.save()

        return broker_quote
    
    
class QuickRequestTemplate(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.title

class BrokerQuote(models.Model):
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )

    quote_request = models.ForeignKey(QuoteRequest, on_delete=models.CASCADE, related_name='quotes')
    broker = models.ForeignKey(BrokerProfile, on_delete=models.CASCADE)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_days = models.IntegerField()

    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('quote_request', 'broker')

    def __str__(self):
        return f"{self.broker.business_name} - {self.total_price}"
