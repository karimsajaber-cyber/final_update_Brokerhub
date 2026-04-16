from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.http import JsonResponse
from django.db.models import Sum, Min, Max, Count, Avg
from django.db.models import Q, Prefetch
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from .models import BrokerProfile
from core.models import Category
from locations.models import City
from requests.models import QuoteRequest, BrokerQuote
from reviews.models import Review


MONEY_STEP = Decimal('0.01')


def as_money(value):
    if value in (None, ''):
        return Decimal('0.00')
    return Decimal(str(value)).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)



def landing_page(request):
    brokers = BrokerProfile.objects.select_related('user', 'city').prefetch_related(
        'platforms__platform__category'
    ).filter(
        is_active=True,
        is_verified=True,
    ).order_by('-average_rating', '-total_reviews', 'business_name')[:3]
    show_ai_assistant = request.session.get('role') == 'customer'
    context = {
        "brokers": brokers,
        "active_brokers": "500+",
        "completed_deals": "10K+",
        "rating": "4.8/5",
        "response_time": "<2h",
        "show_ai_assistant": show_ai_assistant,
    }
    return render(request, "landing_page.html", context)


def about(request):
    errors   = request.session.pop('form_errors', None)
    old_data = request.session.pop('old_data', None)
    context  = {'form_errors': errors, 'old_data': old_data}
    return render(request, 'about_us.html', context)


def browse_brokers(request):
    brokers  = BrokerProfile.objects.select_related('user', 'city').prefetch_related('platforms__platform__category')
    context  = {
        'brokers'   : brokers,
        'categories': Category.objects.all(),
        'cities'    : City.objects.all(),
    }
    return render(request, 'browse_brokers.html', context)


def broker_profile(request, id):
    from reviews.models import Review
    broker = get_object_or_404(BrokerProfile, id=id)
    reviews = Review.objects.filter(broker=broker).select_related('customer').order_by('-created_at')[:3]
    if reviews.exists():
        avg = sum(r.rating for r in reviews) / reviews.count()
        broker.average_rating = round(avg, 1)
        broker.total_reviews = reviews.count()
        broker.save()
    return render(request, "broker_profile.html", {"broker": broker, "reviews": reviews})


def join_broker(request):
    if request.method == "POST":
        return redirect('about')
    return redirect('about')


def filter_brokers(request):
    brokers = BrokerProfile.objects.select_related(
        'user', 'city'
    ).prefetch_related(
        'platforms__platform__category'
    ).all()
    category_id = request.GET.get('category')
    city_id     = request.GET.get('city')
    search      = (request.GET.get('search') or '').strip()

    if category_id:
        brokers = brokers.filter(platforms__platform__category_id=category_id).distinct()
    if city_id:
        brokers = brokers.filter(city_id=city_id)
    if search:
        brokers = brokers.filter(
            Q(business_name__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search)
        ).distinct()

    data = []
    for broker in brokers:
        categories = []
        seen_categories = set()
        for broker_platform in broker.platforms.all():
            category_name = broker_platform.platform.category.name
            if category_name not in seen_categories:
                seen_categories.add(category_name)
                categories.append(category_name)

        display_name = f"{broker.user.first_name} {broker.user.last_name}".strip() or broker.business_name
        avatar_text = (
            broker.user.first_name[:1]
            or broker.business_name[:1]
            or broker.user.username[:1]
            or "B"
        ).upper()

        profile_image_url = None
        if broker.profile_image:
            try:
                profile_image_url = request.build_absolute_uri(broker.profile_image.url)
            except Exception:
                pass

        data.append({
            'id': broker.id,
            'display_name': display_name,
            'business_name': broker.business_name,
            'city': broker.city.name if broker.city else 'Not specified',
            'description': broker.description or 'No description available.',
            'categories': categories,
            'rating': float(broker.average_rating or 0),
            'reviews_count': int(broker.total_reviews or 0),
            'avatar_text': avatar_text,
            'profile_image_url': profile_image_url,
        })

    return JsonResponse({'brokers': data})


def contact_us(request):
    if request.method == 'POST':
        name     = request.POST.get('name')
        email    = request.POST.get('email')
        whatsapp = request.POST.get('whatsapp')
        message  = request.POST.get('message')
        errors   = {}

        if not name:     errors['name']     = "Name is required"
        if not email:    errors['email']    = "Email is required"
        if not whatsapp: errors['whatsapp'] = "WhatsApp is required"
        if not message:  errors['message']  = "Message is required"

        if errors:
            request.session['form_errors'] = errors
            request.session['old_data']    = dict(request.POST)
            return redirect('about')

        try:
            send_mail(
                subject="New Broker Request",
                message=f"Name: {name}\nEmail: {email}\nWhatsApp: {whatsapp}\nMessage: {message}",
                from_email="brokerhub-team@outlook.com",
                recipient_list=["brokerhub-team@outlook.com"],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(request, "Your request has been sent successfully")
    return redirect('/about')



def broker_dashboard(request):

    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect('/login?role=broker&next=/dashboard/')

    try:
        broker = BrokerProfile.objects.get(user_id=request.session['user_id'])
    except BrokerProfile.DoesNotExist:
        return redirect('/admin/')

    total_quotes  = BrokerQuote.objects.filter(broker=broker).count()
    active_quotes = BrokerQuote.objects.filter(broker=broker, status='sent').count()
    won_deals     = BrokerQuote.objects.filter(broker=broker, status='accepted').count()
    total_revenue = BrokerQuote.objects.filter(broker=broker, status='accepted').aggregate(total=Sum('total_price'))['total'] or 0
    acceptance_rate = round((won_deals / total_quotes) * 100, 1) if total_quotes > 0 else 0

    assigned_requests = QuoteRequest.objects.select_related(
        'platform__category', 'city', 'customer'
    ).filter(
        broker=broker,
        status__in=['pending', 'quoted', 'accepted']
    ).order_by('-created_at')

    requests_data = []
    for req in assigned_requests:
        already_quoted = BrokerQuote.objects.filter(quote_request=req, broker=broker).exists()
        quotes_count   = BrokerQuote.objects.filter(quote_request=req).count()
        price_range    = BrokerQuote.objects.filter(quote_request=req).aggregate(
            min_price=Min('total_price'), max_price=Max('total_price')
        )
        requests_data.append({
            'request'       : req,
            'already_quoted': already_quoted,
            'quotes_count'  : quotes_count,
            'min_price'     : price_range['min_price'],
            'max_price'     : price_range['max_price'],
        })

    context = {
        'broker'               : broker,
        'total_quotes'         : total_quotes,
        'active_quotes'        : active_quotes,
        'won_deals'            : won_deals,
        'total_revenue'        : total_revenue,
        'acceptance_rate'      : acceptance_rate,
        'requests_data'        : requests_data,
        'active_requests_count': len(requests_data),
    }
    return render(request, 'brokers/dashboard.html', context)


def broker_stats(request):

    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect('/login?role=broker&next=/broker-stats/')

    broker = BrokerProfile.objects.get(user_id=request.session['user_id'])

    total_quotes = BrokerQuote.objects.filter(broker=broker).count()
    won_deals = BrokerQuote.objects.filter(broker=broker, status='accepted').count()
    win_rate = round((won_deals / total_quotes) * 100) if total_quotes > 0 else 0
    total_revenue = as_money(
        BrokerQuote.objects.filter(broker=broker, status='accepted').aggregate(total=Sum('total_price'))['total']
    )
    avg_deal_value = as_money(
        BrokerQuote.objects.filter(broker=broker, status='accepted').aggregate(avg=Avg('total_price'))['avg']
    )
    avg_rating = broker.average_rating

    now                  = timezone.now()
    current_month_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    def calc_change(current, previous):
        if previous == 0: return '+100%' if current > 0 else 'N/A'
        change = round(((current - previous) / previous) * 100)
        return f'+{change}%' if change > 0 else f'{change}%'

    current_quotes   = BrokerQuote.objects.filter(broker=broker, created_at__gte=current_month_start).count()
    previous_quotes  = BrokerQuote.objects.filter(broker=broker, created_at__gte=previous_month_start, created_at__lt=current_month_start).count()
    current_won      = BrokerQuote.objects.filter(broker=broker, status='accepted', created_at__gte=current_month_start).count()
    previous_won     = BrokerQuote.objects.filter(broker=broker, status='accepted', created_at__gte=previous_month_start, created_at__lt=current_month_start).count()
    current_revenue = as_money(
        BrokerQuote.objects.filter(
            broker=broker,
            status='accepted',
            created_at__gte=current_month_start,
        ).aggregate(total=Sum('total_price'))['total']
    )
    previous_revenue = as_money(
        BrokerQuote.objects.filter(
            broker=broker,
            status='accepted',
            created_at__gte=previous_month_start,
            created_at__lt=current_month_start,
        ).aggregate(total=Sum('total_price'))['total']
    )

    quotes_change    = calc_change(current_quotes, previous_quotes)
    won_change       = calc_change(current_won, previous_won)
    revenue_change   = calc_change(current_revenue, previous_revenue)
    current_wr       = round((current_won / current_quotes * 100) if current_quotes > 0 else 0)
    previous_wr      = round((previous_won / previous_quotes * 100) if previous_quotes > 0 else 0)
    win_rate_change  = calc_change(current_wr, previous_wr)

    monthly_stats = []
    for i in range(3, -1, -1):
        ms  = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        me  = now if i == 0 else (ms.replace(day=28) + timedelta(days=4)).replace(day=1)
        mq  = BrokerQuote.objects.filter(broker=broker, created_at__gte=ms, created_at__lt=me).count()
        mw  = BrokerQuote.objects.filter(broker=broker, status='accepted', created_at__gte=ms, created_at__lt=me).count()
        mr = as_money(
            BrokerQuote.objects.filter(
                broker=broker,
                status='accepted',
                created_at__gte=ms,
                created_at__lt=me,
            ).aggregate(total=Sum('total_price'))['total']
        )
        monthly_stats.append({'month': ms.strftime('%b %Y'), 'quotes': mq, 'won': mw, 'revenue': mr, 'win_percent': round((mw/mq*100) if mq>0 else 0)})

    accepted_quotes    = BrokerQuote.objects.filter(broker=broker, status='accepted').select_related('quote_request__platform__category')
    category_data      = {}
    for quote in accepted_quotes:
        try:
            cat_name = quote.quote_request.platform.category.name
        except Exception:
            cat_name = 'Other'
        if cat_name not in category_data:
            category_data[cat_name] = {'deals': 0, 'revenue': Decimal('0.00')}
        category_data[cat_name]['deals'] += 1
        category_data[cat_name]['revenue'] += as_money(quote.total_price)

    category_breakdown = sorted([
        {
            'category': k,
            'deals': v['deals'],
            'revenue': as_money(v['revenue']),
            'percentage': int(
                ((v['revenue'] / total_revenue) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            ) if total_revenue > 0 else 0,
        }
        for k, v in category_data.items()
    ], key=lambda x: x['revenue'], reverse=True)

    recent_reviews = Review.objects.filter(broker=broker).select_related('customer').order_by('-created_at')[:3][:5]

    context = {
        'broker'            : broker,
        'total_quotes'      : total_quotes,
        'won_deals'         : won_deals,
        'win_rate'          : win_rate,
        'total_revenue'     : total_revenue,
        'avg_deal_value'    : avg_deal_value,
        'avg_rating'        : avg_rating,
        'quotes_change'     : quotes_change,
        'won_change'        : won_change,
        'revenue_change'    : revenue_change,
        'win_rate_change'   : win_rate_change,
        'monthly_stats'     : monthly_stats,
        'category_breakdown': category_breakdown,
        'recent_reviews'    : recent_reviews,
    }
    return render(request, 'brokers/broker_stats.html', context)


def broker_landing(request):
    if 'user_id' not in request.session or request.session.get('role') != 'broker':
        return redirect('/login?role=broker&next=/broker-landing/')
    try:
        broker = BrokerProfile.objects.get(user_id=request.session['user_id'])
    except BrokerProfile.DoesNotExist:
        broker = None
    from requests.models import QuoteRequest
    open_requests = QuoteRequest.objects.filter(status='pending').count()
    context = {
        'broker': broker,
        'open_requests': open_requests,
    }
    return render(request, 'broker_landing.html', context)


def brokers_api(request):
    from django.http import JsonResponse
    category_name = (request.GET.get('category') or '').strip().lower()

    brokers = BrokerProfile.objects.select_related(
        'user', 'city'
    ).prefetch_related('platforms__platform__category').filter(is_active=True)

    data = []
    for b in brokers:
        # Collect category names for this broker
        broker_categories = []
        for bp in b.platforms.all():
            try:
                broker_categories.append(bp.platform.category.name.lower())
            except Exception:
                pass

        # If category filter supplied, skip non-matching brokers
        if category_name and not any(category_name in cat for cat in broker_categories):
            continue

        image_url = None
        if b.profile_image:
            try:
                image_url = request.build_absolute_uri(b.profile_image.url)
            except Exception:
                pass

        data.append({
            'id'        : b.id,
            'name'      : b.business_name,
            'city'      : b.city.name if b.city else '',
            'rating'    : float(b.average_rating or 0),
            'categories': broker_categories,
            'image_url' : image_url,
        })

    return JsonResponse({'brokers': data})


def update_broker_profile(request):
    user_id = request.session.get('user_id')
    if not user_id or request.session.get('role') != 'broker':
        return redirect(f"/login?role=broker&next={request.path}")

    broker = get_object_or_404(BrokerProfile, user_id=user_id)
    cities = City.objects.all()

    if request.method == 'POST':
        broker.business_name = request.POST.get('business_name', broker.business_name).strip() or broker.business_name
        broker.whatsapp_number = request.POST.get('whatsapp_number', broker.whatsapp_number).strip()
        broker.description = request.POST.get('description', broker.description).strip()

        experience_years = request.POST.get('experience_years', '').strip()
        broker.experience_years = int(experience_years) if experience_years.isdigit() else 0

        city_id = request.POST.get('city')
        broker.city = City.objects.filter(id=city_id).first() if city_id else None

        uploaded_image = request.FILES.get('profile_image')
        if uploaded_image:
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if uploaded_image.content_type not in allowed_types:
                messages.error(request, 'Invalid file type. Please upload an image file (JPG, PNG, GIF, or WebP).')
                return redirect('update_broker_profile')
            if uploaded_image.size > 5 * 1024 * 1024:
                messages.error(request, 'Image size must be less than 5MB. Please upload a smaller image.')
                return redirect('update_broker_profile')
            broker.profile_image = uploaded_image

        broker.save()
        messages.success(request, 'Your profile has been successfully updated.')
        return redirect('update_broker_profile')

    return render(
        request,
        'update_profile.html',
        {
            'broker': broker,
            'cities': cities,
        },
    )
