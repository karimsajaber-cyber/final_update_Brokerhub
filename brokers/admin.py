from django.contrib import admin
from .models import BrokerProfile, BrokerPlatform

admin.site.register(BrokerProfile)
admin.site.register(BrokerPlatform)