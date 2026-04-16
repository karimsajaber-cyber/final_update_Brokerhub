from urllib.parse import quote as url_quote

from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import User
from requests.models import BrokerQuote
from reviews.models import Review


def add_review(request, id):

    if 'user_id' not in request.session or request.session.get('role') != 'customer':
        return redirect(f'/login?role=customer&next=/review/{id}/')

    customer = User.objects.get(id=request.session['user_id'])
    broker_quote = get_object_or_404(
        BrokerQuote.objects.select_related('quote_request', 'broker'),
        id=id,
        quote_request__customer_id=customer.id,
    )

    if (broker_quote.quote_request.status or '').lower() != 'completed':
        return redirect(f"/requests/my?notice={url_quote('You can review a broker only after the request is completed.')}")

    broker_quote = broker_quote.quote_request.sync_assigned_quote_from_request_metadata() or broker_quote

    existing_review = Review.objects.filter(
        customer=customer,
        broker_quote=broker_quote
    ).first()

    if request.method == 'POST':

        if existing_review:
            error = "You already reviewed this quote"
            return render(request, 'reviews/review.html', {
                'broker_quote': broker_quote,
                'error': error,
                'existing_review': existing_review
            })

        rating  = request.POST.get('rating')
        comment = request.POST.get('comment')
        error   = None

        if not rating:
            error = 'Please select a rating'
        elif not comment:
            error = 'Please write a review'
        elif len(comment) < 20:
            error = 'Review must be at least 20 characters'

        if error:
            return render(request, 'reviews/review.html', {
                'broker_quote': broker_quote,
                'error': error,
                'existing_review': existing_review
            })

        Review.objects.create(
            customer     = customer,
            broker       = broker_quote.broker,
            broker_quote = broker_quote,
            rating       = int(rating),
            comment      = comment,
        )

        broker = broker_quote.broker
        all_reviews = Review.objects.filter(broker=broker)
        broker.average_rating = round(sum(r.rating for r in all_reviews) / all_reviews.count(), 1)
        broker.total_reviews  = all_reviews.count()
        broker.save()

        return redirect('/requests/my')

    return render(request, 'reviews/review.html', {
        'broker_quote': broker_quote,
        'existing_review': existing_review
    })
