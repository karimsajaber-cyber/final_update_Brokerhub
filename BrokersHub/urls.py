from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from requests import urls as requests_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('brokers.urls')),
    path('', include(requests_urls)),
    path('', include('reviews.urls')),
    path('', include('chat.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
