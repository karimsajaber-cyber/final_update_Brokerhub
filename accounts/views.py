from django.shortcuts import render, redirect
from django.contrib.auth import authenticate
from .models import User


def infer_role_from_next(next_url):
    customer_prefixes = (
        '/create',
        '/requests/my',
        '/review/',
        '/chatbot/',
    )
    broker_prefixes = (
        '/dashboard/',
        '/broker-stats/',
        '/broker-landing/',
        '/requests/broker/',
        '/quote/',
    )

    next_url = next_url or '/'

    if any(next_url.startswith(prefix) for prefix in customer_prefixes) or '/edit' in next_url or '/delete' in next_url:
        return 'customer'
    if any(next_url.startswith(prefix) for prefix in broker_prefixes):
        return 'broker'
    return None


def build_login_url(role, next_url=''):
    login_url = f'/login?role={role}'
    if next_url:
        login_url = f"{login_url}&next={next_url}"
    return login_url


def can_register_from_login(next_url):
    return (next_url or '').startswith('/create')


def get_auth_copy(role, next_url=''):
    if role == 'broker':
        return 'Login', 'Login with your broker account to continue.'
    if role == 'customer' and can_register_from_login(next_url):
        return 'Login', 'Login to continue with your broker request.'
    if role == 'customer':
        return 'Login', 'Login with your customer account to continue.'
    return 'Login', 'Login with your account credentials to continue.'


def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or '/'
    error_message = None
    helper_message = None
    requested_role = (request.GET.get('role') or request.POST.get('role') or '').strip().lower()
    inferred_role = infer_role_from_next(next_url)
    active_role = inferred_role or (requested_role if requested_role in {'customer', 'broker'} else None)
    auth_role_locked = inferred_role is not None or requested_role in {'customer', 'broker'}
    show_register = can_register_from_login(next_url)
    auth_title, auth_text = get_auth_copy(active_role, next_url)

    if 'user_id' in request.session:
        session_role = request.session.get('role')
        if active_role and session_role == active_role:
            if next_url not in {'/', '/login'}:
                return redirect(next_url)
            if active_role == 'broker':
                return redirect('/broker-landing/')
            return redirect('/')
        if not active_role:
            if session_role == 'broker':
                return redirect('/broker-landing/')
            if session_role == 'customer':
                return redirect('/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user and (active_role is None or user.role == active_role):
            request.session['user_id'] = user.id
            request.session['role'] = user.role
            request.session['username'] = user.username
            if user.role == 'broker' and (next_url == '/' or next_url == '/login'):
                return redirect('/broker-landing/')
            return redirect(next_url)

        if user and active_role and user.role != active_role:
            if active_role == 'broker':
                error_message = 'You cannot log in as broker because your role is customer.'
            else:
                error_message = 'You cannot log in as customer because your role is broker.'
        else:
            error_message = 'Invalid username or password.'
            if active_role == 'broker':
                helper_message = 'Broker accounts are added by admin.'

    context = {
        'next': next_url,
        'error_message': error_message,
        'helper_message': helper_message,
        'show_register': show_register,
        'auth_title': auth_title,
        'auth_text': auth_text,
        'active_role': active_role,
        'auth_role_locked': auth_role_locked,
        'customer_login_url': build_login_url('customer', next_url),
        'broker_login_url': build_login_url('broker', next_url),
    }

    return render(request, 'login.html', context)


def register_view(request):
    next_url = request.GET.get('next') or request.POST.get('next') or '/create'
    error_message = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not email or not phone or not password or not confirm_password:
            error_message = 'All fields are required.'
        elif password != confirm_password:
            error_message = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error_message = 'This username already exists.'
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='customer',
                phone=phone,
            )
            request.session['user_id'] = user.id
            request.session['role'] = user.role
            request.session['username'] = user.username
            return redirect(next_url)

    context = {
        'next': next_url,
        'error_message': error_message,
        'customer_login_url': build_login_url('customer', next_url),
    }

    return render(request, 'register.html', context)


def logout_view(request):
    request.session.flush()
    return redirect('/')
