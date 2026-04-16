from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('about', views.about, name='about'),
    path('brokers', views.browse_brokers, name='browse_brokers'),
    path('broker/<int:id>', views.broker_profile, name='broker_profile'),
    path('join-broker', views.join_broker, name='join_broker'),
    path('contact', views.contact_us, name='contact_us'),
    path('browse/', views.browse_brokers, name='browse_brokers_alt'),
    path('filter/', views.filter_brokers, name='filter_brokers'),

    path('dashboard/', views.broker_dashboard, name='broker_dashboard'),
    path('broker-stats/', views.broker_stats, name='broker_stats'),
    path('broker-landing/', views.broker_landing, name='broker_landing'),
    path('profile/update/', views.update_broker_profile, name='update_broker_profile'),
    path('api/brokers/', views.brokers_api, name='brokers_api'),
]
