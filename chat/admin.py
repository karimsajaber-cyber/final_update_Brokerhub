from django.contrib import admin
from .models import Message, Report


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'quote_request', 'sender', 'receiver', 'text', 'created_at', 'is_read']
    list_filter = ['is_read', 'created_at']
    search_fields = ['text', 'sender__email', 'receiver__email']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reporter', 'reported_user', 'message', 'created_at']
    list_filter = ['created_at']
    search_fields = ['reason', 'reporter__email', 'reported_user__email']