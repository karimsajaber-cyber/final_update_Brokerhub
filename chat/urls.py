from django.urls import path

from . import views


urlpatterns = [
    path("chat/", views.chat_home, name="chat_home"),
    path("chat/request/<int:request_id>/", views.chat_conversation, name="chat_conversation"),
    path("chat/request/<int:request_id>/messages/", views.fetch_messages, name="fetch_messages"),
    path("chat/request/<int:request_id>/send/", views.send_message, name="send_message"),
    path("chat/report/", views.create_report, name="create_report"),
]
