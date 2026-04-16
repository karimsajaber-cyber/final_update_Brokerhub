import re
import json
from decimal import Decimal, InvalidOperation
import httpx
from urllib.parse import quote as url_quote
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Min, Max
from django.db import transaction
from django.conf import settings
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from brokers.models import BrokerProfile
from requests.models import QuoteRequest, BrokerQuote, QuickRequestTemplate
from reviews.models import Review
from core.models import Platform


GROQ_API_KEY    = settings.GROQ_API_KEY
GROQ_API_URL    = settings.GROQ_API_URL
GROQ_MODEL      = settings.GROQ_MODEL
RAPIDAPI_KEY    = settings.RAPIDAPI_KEY
AMAZON_API_HOST = settings.AMAZON_API_HOST
SHEIN_API_HOST  = settings.SHEIN_API_HOST
TEMU_API_HOST   = settings.TEMU_API_HOST
BROKER_DELETE_SNAPSHOT_SESSION_KEY = 'broker_deleted_request_snapshot'


def _serialize_model_instance(instance):
    data = {}
    for field in instance._meta.concrete_fields:
        value = getattr(instance, field.attname)
        if isinstance(value, Decimal):
            data[field.attname] = str(value)
        elif hasattr(value, 'isoformat'):
            data[field.attname] = value.isoformat()
        else:
            data[field.attname] = value
    return data


def _deserialize_model_data(model, serialized_data):
    data = {}
    for field in model._meta.concrete_fields:
        if field.attname not in serialized_data:
            continue

        value = serialized_data[field.attname]
        if value is None:
            data[field.attname] = None
            continue

        internal_type = field.get_internal_type()
        if internal_type == 'DecimalField':
            data[field.attname] = Decimal(value)
        elif internal_type == 'DateTimeField':
            data[field.attname] = parse_datetime(value)
        elif internal_type in {'AutoField', 'BigAutoField', 'IntegerField', 'BigIntegerField', 'PositiveIntegerField', 'PositiveSmallIntegerField', 'SmallIntegerField', 'ForeignKey'}:
            data[field.attname] = int(value)
        else:
            data[field.attname] = value
    return data


def _build_broker_delete_snapshot(request_item):
    broker_quotes = list(BrokerQuote.objects.filter(quote_request=request_item).order_by('id'))
    reviews = list(Review.objects.filter(broker_quote__in=broker_quotes).order_by('id'))
    return {
        'request': _serialize_model_instance(request_item),
        'quotes': [_serialize_model_instance(quote) for quote in broker_quotes],
        'reviews': [_serialize_model_instance(review) for review in reviews],
    }


def _restore_deleted_broker_request(snapshot):
    request_data = _deserialize_model_data(QuoteRequest, snapshot['request'])
    quote_data_list = [_deserialize_model_data(BrokerQuote, item) for item in snapshot.get('quotes', [])]
    review_data_list = [_deserialize_model_data(Review, item) for item in snapshot.get('reviews', [])]

    original_request_id = request_data.pop('id', None)
    request_created_at = request_data.pop('created_at', None)
    request_updated_at = request_data.pop('updated_at', None)

    if original_request_id and not QuoteRequest.objects.filter(id=original_request_id).exists():
        request_data['id'] = original_request_id

    restored_request = QuoteRequest.objects.create(**request_data)
    QuoteRequest.objects.filter(pk=restored_request.pk).update(
        created_at=request_created_at,
        updated_at=request_updated_at,
    )

    quote_id_map = {}
    for quote_data in quote_data_list:
        original_quote_id = quote_data.pop('id', None)
        quote_created_at = quote_data.pop('created_at', None)
        quote_updated_at = quote_data.pop('updated_at', None)
        quote_data['quote_request_id'] = restored_request.pk

        if original_quote_id and not BrokerQuote.objects.filter(id=original_quote_id).exists():
            quote_data['id'] = original_quote_id

        restored_quote = BrokerQuote.objects.create(**quote_data)
        BrokerQuote.objects.filter(pk=restored_quote.pk).update(
            created_at=quote_created_at,
            updated_at=quote_updated_at,
        )
        if original_quote_id is not None:
            quote_id_map[original_quote_id] = restored_quote.pk

    for review_data in review_data_list:
        original_review_id = review_data.pop('id', None)
        review_created_at = review_data.pop('created_at', None)
        original_quote_id = review_data.get('broker_quote_id')
        if original_quote_id not in quote_id_map:
            continue

        review_data['broker_quote_id'] = quote_id_map[original_quote_id]
        if original_review_id and not Review.objects.filter(id=original_review_id).exists():
            review_data['id'] = original_review_id

        restored_review = Review.objects.create(**review_data)
        Review.objects.filter(pk=restored_review.pk).update(created_at=review_created_at)

    return restored_request



def create_request(request):
    if 'user_id' not in request.session or request.session.get('role') != 'customer':
        return redirect(f"/login?role=customer&next={url_quote(request.get_full_path())}")

    broker_id = request.GET.get('broker_id') or request.POST.get('broker_id')
    selected_broker = None
    if broker_id:
        selected_broker = BrokerProfile.objects.filter(id=broker_id).first()

    if request.method == 'GET' and not selected_broker:
        return redirect(reverse('browse_brokers'))

    templates     = QuickRequestTemplate.objects.all()
    error_message = request.GET.get('error')
    prefill_name  = request.GET.get('prefill_name', '')
    prefill_url   = request.GET.get('prefill_url', '')

    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        notes        = request.POST.get('notes')
        product_url  = request.POST.get('product_url', '')

        if not product_name or not notes:
            return redirect(f"/create?broker_id={broker_id}")

        if not selected_broker:
            return redirect(reverse('browse_brokers'))

        broker_platform  = selected_broker.platforms.select_related('platform').first()
        selected_platform = broker_platform.platform if broker_platform else Platform.objects.first()

        if not selected_platform:
            return redirect(f"/create?broker_id={broker_id}&error={url_quote('No platform available.')}")

        QuoteRequest.objects.create(
            product_name=product_name,
            notes=notes,
            customer_id=request.session['user_id'],
            broker=selected_broker,
            product_url=product_url,
            platform=selected_platform,
            city=selected_broker.city if selected_broker.city else None,
        )
        return redirect('/requests/my')

    context = {
        'templates'      : templates,
        'selected_broker': selected_broker,
        'error_message'  : error_message,
        'prefill_name'   : prefill_name,
        'prefill_url'    : prefill_url,
    }
    return render(request, 'create_request.html', context)


def my_requests(request):
    if 'user_id' not in request.session or request.session.get('role') != 'customer':
        return redirect(f"/login?role=customer&next={url_quote(request.get_full_path())}")

    customer_requests = QuoteRequest.objects.select_related(
        'platform', 'city', 'broker'
    ).filter(
        customer_id=request.session['user_id']
    ).order_by('-created_at')

    customer_id = request.session['user_id']
    for req in customer_requests:
        status = (req.status or '').lower()

        assigned_quote = BrokerQuote.objects.filter(
            quote_request=req
        ).order_by('-updated_at', '-created_at').first()

        if assigned_quote is None and status in ('completed', 'accepted'):
            try:
                from brokers.models import BrokerProfile as BP
                bp = BP.objects.filter(user_id__isnull=False).filter(
                    pk=req.broker_id
                ).first() if req.broker_id else None
                if bp:
                    assigned_quote = BrokerQuote.objects.create(
                        quote_request=req,
                        broker=bp,
                        total_price=1,
                        delivery_days=1,
                        status='accepted',
                    )
            except Exception:
                pass

        existing_review = None
        if assigned_quote:
            existing_review = Review.objects.filter(
                customer_id=customer_id,
                broker_quote=assigned_quote,
            ).first()

        req.review_quote_id = assigned_quote.id if assigned_quote else None
        req.can_contact_broker = (
            status == 'accepted'
            and bool(req.broker_id)
        )
        req.can_rate_broker = (
            status == 'completed'
            and assigned_quote is not None
            and existing_review is None
        )
        req.has_review = existing_review is not None

        notes = req.notes or ''
        if assigned_quote is not None:
            req.assigned_price = assigned_quote.total_price
            req.assigned_delivery = assigned_quote.delivery_days
        else:
            price_match = re.search(r'\[Price: \$([^\]]+)\]', notes)
            delivery_match = re.search(r'\[Delivery: ([^\]]+) days\]', notes)
            req.assigned_price = price_match.group(1) if price_match else None
            req.assigned_delivery = delivery_match.group(1) if delivery_match else None
        req.clean_notes = re.sub(r'\[Price:[^\]]+\]|\[Delivery:[^\]]+\]', '', notes).strip()

    context = {
        'customer_requests': customer_requests,
        'notice_message'   : request.GET.get('notice'),
    }
    return render(request, 'my_requests.html', context)


def edit_request(request, id):
    if 'user_id' not in request.session or request.session.get('role') != 'customer':
        return redirect(f"/login?role=customer&next={url_quote(request.get_full_path())}")

    request_item = get_object_or_404(QuoteRequest, id=id, customer_id=request.session['user_id'])

    if (request_item.status or '').lower() != 'pending':
        return redirect(f"/requests/my?notice={url_quote('You can only edit a pending request.')}")

    error_message = request.GET.get('error')

    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        notes        = request.POST.get('notes')
        product_url  = request.POST.get('product_url', '')

        if not product_name or not notes:
            return redirect(f"/requests/{id}/edit?error={url_quote('Title and description are required.')}")

        request_item.product_name = product_name
        request_item.notes        = notes
        request_item.save()
        return redirect(f"/requests/my?notice={url_quote('Your request was updated successfully.')}")

    context = {
        'request_item'  : request_item,
        'selected_broker': request_item.broker,
        'error_message' : error_message,
    }
    return render(request, 'edit_request.html', context)


def delete_request(request, id):
    if 'user_id' not in request.session or request.session.get('role') != 'customer':
        return redirect(f"/login?role=customer&next={url_quote(request.get_full_path())}")

    request_item = get_object_or_404(QuoteRequest, id=id, customer_id=request.session['user_id'])

    allowed_statuses = {'pending', 'cancelled'}
    if (request_item.status or '').lower() not in allowed_statuses:
        return redirect(f"/requests/my?notice={url_quote('You can only delete pending or cancelled requests.')}")

    if request.method == 'POST':
        request_item.delete()
        return redirect(f"/requests/my?notice={url_quote('Your request was deleted successfully.')}")

    return redirect('/requests/my')


def broker_requests(request):
    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect(f"/login?role=broker&next={url_quote(request.get_full_path())}")

    assigned_requests = QuoteRequest.objects.select_related(
        'customer', 'platform', 'city', 'broker'
    ).filter(broker__user_id=request.session['user_id']).order_by('-created_at')

    context = {
        'assigned_requests': assigned_requests,
        'notice_message'   : request.GET.get('notice'),
    }
    return render(request, 'broker_requests.html', context)


def broker_request_details(request, id):
    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect(f"/login?role=broker&next={url_quote(request.get_full_path())}")

    request_item = get_object_or_404(
        QuoteRequest.objects.select_related('customer', 'platform', 'city', 'broker'),
        id=id,
        broker__user_id=request.session['user_id']
    )
    broker_profile = get_object_or_404(BrokerProfile, user_id=request.session['user_id'])
    broker_quote = request_item.sync_assigned_quote_from_request_metadata()

    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        current_status = (request_item.status or '').lower()

        if action_type == 'complete':
            if current_status != 'accepted':
                return redirect(f"/requests/broker/{id}?notice={url_quote('Only an accepted request can be marked as completed.')}")

            broker_quote = request_item.sync_assigned_quote_from_request_metadata()
            if not broker_quote or broker_quote.total_price <= 0:
                return redirect(f"/requests/broker/{id}?notice={url_quote('Add a valid suggested price before completing this request.')}")

            request_item.status = 'completed'
            request_item.save()

            if broker_quote.status != 'accepted':
                broker_quote.status = 'accepted'
                broker_quote.save()

            return redirect(f"/requests/broker/{id}?notice={url_quote('The request has been marked as completed.')}")

        if current_status not in {'pending', 'quoted'}:
            return redirect(f"/requests/broker/{id}?notice={url_quote('This request has already been updated.')}")

        if action_type == 'accept':
            delivery_days = request.POST.get('delivery_days', '').strip()
            price = request.POST.get('price', '').strip()

            if not price:
                return redirect(f"/requests/broker/{id}?notice={url_quote('Suggested price is required.')}")

            try:
                price_value = Decimal(price)
            except InvalidOperation:
                return redirect(f"/requests/broker/{id}?notice={url_quote('Suggested price must be a valid number.')}")

            if price_value <= 0:
                return redirect(f"/requests/broker/{id}?notice={url_quote('Suggested price must be greater than 0.')}")

            if not delivery_days:
                return redirect(f"/requests/broker/{id}?notice={url_quote('Delivery days are required.')}")

            try:
                delivery_days_value = int(delivery_days)
            except ValueError:
                return redirect(f"/requests/broker/{id}?notice={url_quote('Delivery days must be a valid number.')}")

            if delivery_days_value <= 0:
                return redirect(f"/requests/broker/{id}?notice={url_quote('Delivery days must be greater than 0.')}")

            broker_quote, created = BrokerQuote.objects.get_or_create(
                quote_request=request_item,
                broker=broker_profile,
                defaults={
                    'total_price': price_value,
                    'delivery_days': delivery_days_value,
                    'status': 'accepted',
                },
            )
            if not created:
                broker_quote.total_price = price_value
                broker_quote.delivery_days = delivery_days_value
                broker_quote.status = 'accepted'
                broker_quote.save()

            request_item.status = 'accepted'
            request_item.save()
            return redirect(f"/requests/broker/{id}?notice={url_quote('The request was accepted successfully.')}")

        if action_type == 'reject':
            broker_quote = BrokerQuote.objects.filter(
                quote_request=request_item,
                broker=broker_profile,
            ).first()
            if broker_quote and broker_quote.status != 'rejected':
                broker_quote.status = 'rejected'
                broker_quote.save()

            request_item.status = 'cancelled'
            request_item.save()
            return redirect(f"/requests/broker/{id}?notice={url_quote('The request was rejected successfully.')}")

    context = {
        'request_item'  : request_item,
        'broker_quote'  : broker_quote,
        'notice_message': request.GET.get('notice'),
    }
    return render(request, 'broker_request_details.html', context)


def broker_delete_request(request, id):
    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect(f"/login?role=broker&next={url_quote(request.get_full_path())}")

    request_item = get_object_or_404(
        QuoteRequest.objects.select_related('broker'),
        id=id,
        broker__user_id=request.session['user_id']
    )

    if (request_item.status or '').lower() != 'completed':
        return redirect(f"/requests/broker/{id}?notice={url_quote('Only a completed request can be deleted.')}")

    if request.method != 'POST':
        return redirect(f"/requests/broker/{id}/")

    request.session[BROKER_DELETE_SNAPSHOT_SESSION_KEY] = _build_broker_delete_snapshot(request_item)
    request.session.modified = True
    request_item.delete()
    return redirect('/requests/broker/')


def undo_broker_delete_request(request):
    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect(f"/login?role=broker&next={url_quote(request.get_full_path())}")

    if request.method != 'POST':
        return redirect('/requests/broker/')

    snapshot = request.session.get(BROKER_DELETE_SNAPSHOT_SESSION_KEY)
    if not snapshot:
        return redirect(f"/requests/broker/?notice={url_quote('There is no deleted request to restore.')}")

    try:
        with transaction.atomic():
            restored_request = _restore_deleted_broker_request(snapshot)
    except Exception:
        return redirect(
            f"/requests/broker/?notice={url_quote('The deleted request could not be restored. Please try again.')}"
        )

    request.session.pop(BROKER_DELETE_SNAPSHOT_SESSION_KEY, None)
    request.session.modified = True
    return redirect(
        f"/requests/broker/{restored_request.id}/?notice={url_quote('The deleted request was restored successfully.')}"
    )



def submit_quote(request, id):
    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect(f"/login?role=broker&next={url_quote(request.get_full_path())}")

    broker = BrokerProfile.objects.get(user_id=request.session['user_id'])
    quote_request = get_object_or_404(QuoteRequest, id=id, broker=broker)

    already_quoted = BrokerQuote.objects.filter(quote_request=quote_request, broker=broker).exists()
    if already_quoted:
        return redirect('/dashboard/')

    price_range  = BrokerQuote.objects.filter(quote_request=quote_request).aggregate(
        min_price=Min('total_price'), max_price=Max('total_price')
    )
    quotes_count = BrokerQuote.objects.filter(quote_request=quote_request).count()

    if request.method == 'POST':
        total_price   = request.POST.get('total_price')
        delivery_days = request.POST.get('delivery_days')
        notes         = request.POST.get('notes')
        error         = None

        if not total_price:
            error = 'Price is required'
        elif float(total_price) <= 0:
            error = 'Price must be greater than 0'
        elif not delivery_days:
            error = 'Delivery days is required'
        elif int(delivery_days) <= 0:
            error = 'Delivery days must be greater than 0'

        if error:
            return render(request, 'requests/submit_quote.html', {
                'quote_request': quote_request, 'price_range': price_range,
                'quotes_count': quotes_count, 'error': error,
            })

        BrokerQuote.objects.create(
            quote_request=quote_request, broker=broker,
            total_price=total_price, delivery_days=delivery_days, notes=notes,
        )
        quote_request.status = 'quoted'
        quote_request.save()
        return redirect('/dashboard/')

    return render(request, 'requests/submit_quote.html', {
        'quote_request': quote_request,
        'price_range'  : price_range,
        'quotes_count' : quotes_count,
    })


def chatbot_page(request):
    if 'user_id' not in request.session or request.session.get('role') != 'customer':
        return redirect('/login?role=customer&next=/chatbot/')
    initial_payload = request.session.pop('assistant_initial_payload', None)
    return render(request, 'requests/chatbot.html', {'initial_payload': initial_payload})


@csrf_exempt
def chatbot_search(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if 'user_id' not in request.session:
        return JsonResponse({'error': 'Login required'}, status=401)

    data     = json.loads(request.body)
    message  = data.get('message', '').strip()
    msg_type = data.get('type', 'chat')
    history  = data.get('history', [])
    source   = data.get('source', 'landing_widget')

    if not message:
        return JsonResponse({'error': 'Message is required'}, status=400)

    groq_headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type' : 'application/json',
    }

    if msg_type == 'chat':
        # Count questions already asked by the AI
        assistant_turns = sum(1 for h in history if h.get('role') == 'assistant')

        # Force a search if the AI has already asked 3 questions (4th response must be SEARCH)
        if assistant_turns >= 3:
            # Build product description from the full conversation
            convo_summary = ' '.join(
                h['content'] for h in history if h.get('role') == 'user'
            ) + ' ' + message
            return do_search(convo_summary.strip(), message, groq_headers, request=request, source=source)

        at_limit_note = (
            'IMPORTANT: You have asked 3 questions already. This is your LAST allowed question — make it comprehensive to gather all remaining details (brand, model, specs, color, size) in ONE question.'
            if assistant_turns == 2
            else ''
        )

        system_prompt = f'''You are a smart shopping assistant for BrokersHub — a platform where customers buy products through trusted brokers.
Your job is to understand exactly what product the customer wants, then trigger a search.

STRICT RULES:
1. You may ask at most 4 questions total across the entire conversation. You have asked {assistant_turns} so far.
2. Make each question COMPREHENSIVE — combine category, brand, model, specs, and preferences into one clear question when possible.
3. When you have enough info (brand + model minimum), respond with EXACTLY:
   SEARCH: <product name>
   Example: SEARCH: iPhone 15 Pro 256GB Black
4. Reply in the same language as the user (Arabic or English).
5. Be friendly and direct.
{at_limit_note}

CATEGORIES you support:
- Electronics → Phones, Laptops, Headphones, Cameras, Tablets
- Fashion → Men / Women / Kids clothing, shoes, accessories
- Shopping → General everyday products
- Home and Living → Furniture, Kitchen, Decor, Bedding
- Sports → Equipment, Clothing, Shoes'''

        messages_list = [{'role': 'system', 'content': system_prompt}]
        for h in history:
            messages_list.append({'role': h['role'], 'content': h['content']})

        try:
            chat_res = httpx.post(GROQ_API_URL, headers=groq_headers, json={
                'model': GROQ_MODEL, 'messages': messages_list, 'max_tokens': 180,
            }, timeout=10)
            ai_reply = chat_res.json()['choices'][0]['message']['content']
        except Exception as e:
            return JsonResponse({'type': 'chat', 'message': 'What product are you looking for?'})

        if ai_reply.strip().startswith('SEARCH:'):
            product_name = ai_reply.replace('SEARCH:', '').strip()
            detected_category = _detect_category(history, message)
            return do_search(product_name, message, groq_headers, detected_category, request=request, source=source)

        return JsonResponse({'type': 'chat', 'message': ai_reply})

    detected_category = _detect_category(history, message)
    return do_search(message, message, groq_headers, detected_category, request=request, source=source)


def _detect_category(history, current_message):
    """Infer the product category from the conversation so far."""
    all_text = ' '.join(
        h.get('content', '') for h in history
    ) + ' ' + current_message
    all_text = all_text.lower()

    category_keywords = {
        'electronics': [
            'phone', 'iphone', 'samsung', 'laptop', 'macbook', 'headphone', 'airpods',
            'camera', 'tablet', 'ipad', 'tv', 'television', 'playstation', 'xbox',
            'console', 'drone', 'speaker', 'watch', 'smartwatch', 'earbuds', 'monitor',
        ],
        'fashion': [
            'dress', 'shirt', 'jacket', 'clothes', 'clothing', 'fashion', 'shein',
            'asos', 'shoes', 'sneakers', 'jeans', 'pants', 'skirt', 'hoodie', 'top',
            'blazer', 'coat', 'wear', 'outfit', 'style',
        ],
        'shopping': [
            'temu', 'product', 'item', 'buy', 'order', 'general', 'everyday',
            'storage', 'organizer', 'gadget', 'accessories',
        ],
        'home & living': [
            'furniture', 'sofa', 'chair', 'table', 'bed', 'kitchen', 'home',
            'decor', 'ikea', 'shelf', 'lamp', 'rug', 'curtain', 'vacuum', 'dyson',
        ],
        'sports': [
            'nike', 'adidas', 'sport', 'gym', 'running', 'football', 'shoes',
            'equipment', 'fitness', 'workout', 'basketball', 'soccer',
        ],
    }

    for category, keywords in category_keywords.items():
        if any(kw in all_text for kw in keywords):
            return category
    return ''


def do_search(product_name, original_message, groq_headers, detected_category='', request=None, source='landing_widget'):
    amazon_results = []
    amazon_price   = None
    try:
        amazon_res  = httpx.get(
            f'https://{AMAZON_API_HOST}/search-v2',
            headers={'X-RapidAPI-Key': RAPIDAPI_KEY, 'X-RapidAPI-Host': AMAZON_API_HOST},
            params={'q': product_name, 'country': 'us', 'limit': '3'},
            timeout=10
        )
        amazon_data = amazon_res.json()
        if amazon_data.get('status') == 'OK':
            for item in amazon_data.get('data', {}).get('products', [])[:3]:
                price_str = item.get('offer', {}).get('price', '')
                amazon_results.append({
                    'platform': 'Amazon', 'name': item.get('product_title', ''),
                    'price': price_str, 'url': item.get('product_url', ''),
                    'image': item.get('product_photos', [''])[0], 'note': '',
                })
                if not amazon_price and price_str:
                    try: amazon_price = float(price_str.replace('$', '').replace(',', '').strip())
                    except: pass
    except Exception as e:
        print("AMAZON ERROR:", e)

    shein_results = []
    try:
        shein_res  = httpx.post(GROQ_API_URL, headers=groq_headers, json={
            'model': GROQ_MODEL,
            'messages': [
                {'role': 'system', 'content': 'Estimate if this product is sold on Shein and its price. Return ONLY JSON: {"available": true, "price": "$25.99", "note": "Estimated price"} or {"available": false}'},
                {'role': 'user', 'content': f'Product: {product_name}'}
            ], 'max_tokens': 60,
        }, timeout=10)
        shein_data = json.loads(shein_res.json()['choices'][0]['message']['content'])
        if shein_data.get('available'):
            shein_results.append({
                'platform': 'Shein', 'name': product_name,
                'price': shein_data.get('price', 'N/A'),
                'url': f'https://www.shein.com/search?q={product_name.replace(" ", "+")}',
                'image': '', 'note': shein_data.get('note', 'Estimated price'),
            })
    except Exception as e:
        print("SHEIN ERROR:", e)

    temu_results = []
    try:
        temu_res  = httpx.post(GROQ_API_URL, headers=groq_headers, json={
            'model': GROQ_MODEL,
            'messages': [
                {'role': 'system', 'content': 'Estimate if this product is sold on Temu and its price (usually 30-60% cheaper than Amazon). Return ONLY JSON: {"available": true, "price": "$15.99", "note": "Estimated price"} or {"available": false}'},
                {'role': 'user', 'content': f'Product: {product_name}. Amazon price: ${amazon_price or "unknown"}'}
            ], 'max_tokens': 60,
        }, timeout=10)
        temu_data = json.loads(temu_res.json()['choices'][0]['message']['content'])
        if temu_data.get('available'):
            temu_results.append({
                'platform': 'Temu', 'name': product_name,
                'price': temu_data.get('price', 'N/A'),
                'url': f'https://www.temu.com/search?q={product_name.replace(" ", "+")}',
                'image': '', 'note': temu_data.get('note', 'Estimated price'),
            })
    except Exception as e:
        print("TEMU ERROR:", e)

    all_results = amazon_results + shein_results + temu_results

    if all_results:
        try:
            analyze_res = httpx.post(GROQ_API_URL, headers=groq_headers, json={
                'model': GROQ_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'Smart shopping assistant. Give a short friendly summary. Mention cheapest option. Note Shein/Temu are estimated prices. Max 2 sentences. Same language as user.'},
                    {'role': 'user', 'content': f'Searched: {original_message}\nResults: {json.dumps(all_results, ensure_ascii=False)}'}
                ], 'max_tokens': 150,
            }, timeout=10)
            ai_summary = analyze_res.json()['choices'][0]['message']['content']
        except:
            ai_summary = f"Found {len(all_results)} results for '{product_name}'."
    else:
        ai_summary = f"Sorry, I couldn't find results for '{product_name}'."

    payload = {
        'type': 'search', 'product_name': product_name,
        'ai_summary': ai_summary, 'results': all_results,
        'has_results': len(all_results) > 0,
        'detected_category': detected_category,
        'original_message': original_message,
    }

    if payload['has_results'] and request is not None and request.session.get('role') == 'customer':
        request.session['assistant_initial_payload'] = dict(payload)
        request.session.modified = True
        if source != 'assistant_page':
            payload['assistant_redirect_url'] = reverse('chatbot_page')

    return JsonResponse(payload)


def customer_request_details(request, id):
    if 'user_id' not in request.session or request.session.get('role') != 'customer':
        return redirect(f"/login?role=customer&next=/requests/my/{id}/")

    request_item = get_object_or_404(
        QuoteRequest.objects.select_related('customer', 'platform', 'city', 'broker'),
        id=id,
        customer_id=request.session['user_id']
    )

    import re as re_mod
    notes = request_item.notes or ''
    assigned_quote = request_item.sync_assigned_quote_from_request_metadata()
    if assigned_quote is not None:
        request_item.assigned_price = assigned_quote.total_price
        request_item.assigned_delivery = assigned_quote.delivery_days
    else:
        price_match = re_mod.search(r'\[Price: \$([^\]]+)\]', notes)
        delivery_match = re_mod.search(r'\[Delivery: ([^\]]+) days\]', notes)
        request_item.assigned_price = price_match.group(1) if price_match else None
        request_item.assigned_delivery = delivery_match.group(1) if delivery_match else None
    request_item.clean_notes = re_mod.sub(r'\[Price:[^\]]+\]|\[Delivery:[^\]]+\]', '', notes).strip()

    return render(request, 'customer_request_details.html', {'request_item': request_item})
