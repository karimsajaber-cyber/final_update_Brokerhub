from django.contrib import admin
from .models import QuoteRequest, BrokerQuote , QuickRequestTemplate

admin.site.register(QuoteRequest)
admin.site.register(BrokerQuote)
admin.site.register(QuickRequestTemplate)