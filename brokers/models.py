from django.db import models
from accounts.models import User
from locations.models import City
from core.models import Platform

class BrokerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='broker_profile')

    business_name = models.CharField(max_length=255)
    profile_image = models.ImageField(upload_to='brokers/avatars/', null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)

    whatsapp_number = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    average_rating = models.FloatField(default=0)
    total_reviews = models.IntegerField(default=0)

    show_whatsapp_after_accept = models.BooleanField(default=True)

    def __str__(self):
        return self.business_name


class BrokerPlatform(models.Model):
    broker = models.ForeignKey(BrokerProfile, on_delete=models.CASCADE, related_name='platforms')
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('broker', 'platform')

    def __str__(self):
        return f"{self.broker.business_name} - {self.platform.name}"
