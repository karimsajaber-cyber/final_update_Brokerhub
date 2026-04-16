from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_request, name='create_request'),
    path('requests/my/', views.my_requests, name='my_requests'),
    path('requests/broker/', views.broker_requests, name='broker_requests'),
    path('requests/broker/undo-delete/', views.undo_broker_delete_request, name='undo_broker_delete_request'),
    path('requests/broker/<int:id>/', views.broker_request_details, name='broker_request_details'),
    path('requests/broker/<int:id>/delete/', views.broker_delete_request, name='broker_delete_request'),
    path('requests/<int:id>/edit/', views.edit_request, name='edit_request'),
    path('requests/<int:id>/delete/', views.delete_request, name='delete_request'),
    path('requests/my/<int:id>/', views.customer_request_details, name='customer_request_details'),

    path('quote/<int:id>/', views.submit_quote, name='submit_quote'),
    path('chatbot/', views.chatbot_page, name='chatbot_page'),
    path('chatbot/search/', views.chatbot_search, name='chatbot_search'),
]
