import json
from urllib.parse import quote as url_quote

from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import User
from requests.models import QuoteRequest

from .models import Message, Report


def _get_session_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return User.objects.filter(id=user_id).first()


def _login_redirect(request):
    return redirect(f"/login?next={url_quote(request.get_full_path())}")


def _conversation_queryset(user):
    base_queryset = QuoteRequest.objects.select_related(
        "customer",
        "broker",
        "broker__user",
        "platform",
        "city",
    ).filter(
        broker__isnull=False,
        broker__user__isnull=False,
    )

    if user.role == "customer":
        return base_queryset.filter(customer_id=user.id)
    if user.role == "broker":
        return base_queryset.filter(broker__user_id=user.id)
    return base_queryset.none()


def _get_conversation_or_404(user, request_id):
    return get_object_or_404(_conversation_queryset(user), id=request_id)


def _get_other_user(chat_request, current_user):
    if chat_request.customer_id == current_user.id:
        return chat_request.broker.user
    return chat_request.customer


def _get_other_label(chat_request, current_user):
    if chat_request.customer_id == current_user.id:
        return chat_request.broker.business_name
    return chat_request.customer.username


def _build_conversation_cards(user, active_request_id=None):
    conversations = _conversation_queryset(user).annotate(
        unread_count=Count(
            "messages",
            filter=Q(messages__receiver_id=user.id, messages__is_read=False),
        ),
        latest_message_at=Max("messages__created_at"),
    ).order_by("-latest_message_at", "-updated_at", "-id")

    cards = []
    for item in conversations:
        partner_image_url = None
        if user.role == 'customer' and item.broker and item.broker.profile_image:
            try:
                partner_image_url = item.broker.profile_image.url
            except Exception:
                pass

        cards.append(
            {
                "request_id": item.id,
                "title": item.product_name,
                "partner": _get_other_label(item, user),
                "status": item.status.title(),
                "platform": item.platform.name,
                "updated_at": item.latest_message_at or item.updated_at,
                "unread_count": item.unread_count,
                "is_active": item.id == active_request_id,
                "partner_image_url": partner_image_url,
            }
        )
    return cards


def _serialize_message(message, current_user_id):
    return {
        "id": message.id,
        "content": message.content,
        "timestamp": message.timestamp.strftime("%b %d, %I:%M %p"),
        "is_mine": message.sender_id == current_user_id,
        "is_read": message.is_read,
        "sender_name": message.sender.username,
        "can_report": message.sender_id != current_user_id,
    }


def chat_home(request):
    user = _get_session_user(request)
    if not user:
        return _login_redirect(request)

    conversation_cards = _build_conversation_cards(user)
    if conversation_cards:
        return redirect(reverse("chat_conversation", args=[conversation_cards[0]["request_id"]]))

    return render(
        request,
        "chat/chat_page.html",
        {
            "chat_user": user,
            "conversation_cards": conversation_cards,
            "active_request": None,
            "chat_partner": None,
        },
    )


def chat_conversation(request, request_id):
    user = _get_session_user(request)
    if not user:
        return _login_redirect(request)

    active_request = _get_conversation_or_404(user, request_id)
    chat_partner = _get_other_user(active_request, user)

    chat_partner_image_url = None
    if user.role == 'customer' and active_request.broker and active_request.broker.profile_image:
        try:
            chat_partner_image_url = active_request.broker.profile_image.url
        except Exception:
            pass

    return render(
        request,
        "chat/chat_page.html",
        {
            "chat_user": user,
            "conversation_cards": _build_conversation_cards(user, active_request.id),
            "active_request": active_request,
            "chat_partner": chat_partner,
            "chat_partner_label": _get_other_label(active_request, user),
            "chat_partner_image_url": chat_partner_image_url,
        },
    )


def fetch_messages(request, request_id):
    user = _get_session_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)

    active_request = _get_conversation_or_404(user, request_id)
    after_id = request.GET.get("after_id")
    message_queryset = Message.objects.select_related("sender", "receiver").filter(
        quote_request=active_request
    )

    Message.objects.filter(
        quote_request=active_request,
        receiver_id=user.id,
        is_read=False,
    ).update(is_read=True)

    if after_id and after_id.isdigit():
        message_queryset = message_queryset.filter(id__gt=int(after_id))

    messages = [
        _serialize_message(message, user.id)
        for message in message_queryset.order_by("id")
    ]
    return JsonResponse({"messages": messages})


def send_message(request, request_id):
    user = _get_session_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    active_request = _get_conversation_or_404(user, request_id)
    content = (request.POST.get("content") or "").strip()
    if not content:
        return JsonResponse({"error": "Message cannot be empty."}, status=400)

    receiver = _get_other_user(active_request, user)
    if receiver.id == user.id:
        return JsonResponse({"error": "You cannot send a message to yourself."}, status=400)

    message = Message.objects.create(
        quote_request=active_request,
        sender=user,
        receiver=receiver,
        text=content,
    )
    return JsonResponse({"message": _serialize_message(message, user.id)})


def create_report(request):
    user = _get_session_user(request)
    if not user:
        return JsonResponse({"error": "Authentication required."}, status=401)
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    payload = {}
    if request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {}

    message_id = payload.get("message_id") or request.POST.get("message_id")
    reason = (payload.get("reason") or request.POST.get("reason") or "").strip()

    if not message_id:
        return JsonResponse({"error": "A message is required for reporting."}, status=400)

    message = get_object_or_404(
        Message.objects.select_related(
            "sender",
            "receiver",
            "quote_request",
            "quote_request__broker",
            "quote_request__broker__user",
            "quote_request__customer",
        ),
        id=message_id,
    )

    if not _conversation_queryset(user).filter(id=message.quote_request_id).exists():
        return JsonResponse({"error": "You cannot report this message."}, status=403)

    if message.sender_id == user.id:
        return JsonResponse({"error": "You cannot report yourself."}, status=400)

    if Report.objects.filter(reporter=user, message=message).exists():
        return JsonResponse({"error": "You already reported this message."}, status=400)

    Report.objects.create(
        reporter=user,
        reported_user=message.sender,
        message=message,
        reason=reason,
    )
    return JsonResponse({"success": True, "message": "Report submitted successfully."})
