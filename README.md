# BrokersHub

A role-based brokerage platform that connects customers with brokers and manages the full request lifecycle, from finding the right broker to completing the deal and leaving a review.

## Overview

BrokersHub was built to make broker-assisted purchasing more organized and transparent.

Customers can browse brokers, filter them by category or city, submit product requests, follow their progress, and review the broker after the request is completed. Brokers receive assigned requests, provide pricing and delivery estimates, update request statuses, and manage their customer interactions through a dedicated workflow.

The platform also includes an AI-assisted shopping experience that helps customers clarify what they are looking for and explore product options before submitting a request.

## Core Features

### Customer Experience

- Create a customer account and sign in securely.
- Browse available brokers and view their profiles.
- Filter brokers by service category, city, or search term.
- Submit a product request to a selected broker.
- Add the product name, product link, and request details.
- Edit or delete requests while they are still pending.
- Track each request through its current status.
- Access the broker's WhatsApp number after acceptance when enabled.
- Review and rate the broker after the request is completed.

### Broker Experience

- Sign in through a broker-specific authentication flow.
- View assigned customer requests.
- Review request details and customer requirements.
- Provide a suggested price and delivery period.
- Accept or reject requests.
- Mark accepted requests as completed.
- Maintain a business profile with supported platforms, location, verification status, and rating information.

### Request and Deal Tracking

Each request moves through a structured workflow:

- `Pending`
- `Quoted`
- `Accepted`
- `Completed`
- `Cancelled`

Broker quotations also have their own statuses:

- `Sent`
- `Accepted`
- `Rejected`

This structure gives customers and brokers a clear view of where each request stands and what action is required next.

### AI-Assisted Product Search

BrokersHub includes a conversational shopping assistant powered by the Groq API.

The assistant:

- Communicates in Arabic or English based on the customer's language.
- Asks focused questions to understand the requested product.
- Narrows the search by category, brand, model, and specifications.
- Searches for relevant Amazon products through RapidAPI.
- Provides estimated comparisons for Shein and Temu when applicable.
- Summarizes the available options and highlights the lowest-priced result.
- Can pass a selected product name and link into the request form.

Estimated prices are presented as estimates and are not treated as confirmed marketplace prices.

### Reviews and Ratings

Customers can review a broker only after a request has been completed.

The review system:

- Prevents duplicate reviews for the same completed quotation.
- Requires a rating and written feedback.
- Recalculates the broker's average rating.
- Tracks the broker's total number of reviews.

## Technology Stack

| Area | Technology |
| --- | --- |
| Backend | Python, Django 6.0.3 |
| Frontend | Django Templates, HTML, CSS, JavaScript |
| Database | SQLite |
| Authentication | Django authentication with a custom user model |
| AI Integration | Groq API |
| Product Search | Amazon Search through RapidAPI |
| HTTP Client | HTTPX |
| Email Testing | SMTP with Mailtrap |
| Version Control | Git and GitHub |

## Project Structure

```text
Brokers_Hub_2026/
├── BrokersHub/        # Main Django project configuration
├── accounts/          # Custom users, registration, login, and roles
├── brokers/           # Broker profiles, broker directory, and filtering
├── core/              # Categories and supported platforms
├── locations/         # City data
├── requests/          # Customer requests, broker quotes, and AI search
├── reviews/           # Customer reviews and broker rating updates
├── manage.py
└── README.md
```

## User Roles

BrokersHub uses a custom Django user model with three roles:

- **Customer:** Searches for brokers, creates requests, follows deals, and submits reviews.
- **Broker:** Manages assigned requests, provides prices, and updates deal status.
- **Admin:** Manages platform data and user records through Django administration.

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/karimsajaber-cyber/Brokers_Hub_2026.git
cd Brokers_Hub_2026
```

The current development work is available on the `karim-work` branch:

```bash
git checkout karim-work
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv env
env\Scripts\activate
```

macOS or Linux:

```bash
python3 -m venv env
source env/bin/activate
```

### 3. Install the core dependencies

```bash
pip install Django==6.0.3 httpx
```

### 4. Apply database migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create an administrator account

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

Open the application at:

```text
http://127.0.0.1:8000/
```

## Initial Data

After creating a superuser, use the Django admin panel to add the initial platform data:

- Cities
- Categories
- Shopping platforms
- Broker accounts
- Broker profiles
- Broker-supported platforms

The administration panel is available at:

```text
http://127.0.0.1:8000/admin/
```

## Configuration and Security

The AI assistant, Amazon product search, and email features require external credentials.

Recommended environment variables:

```env
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True

EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

GROQ_API_KEY=
GROQ_API_URL=
GROQ_MODEL=

RAPIDAPI_KEY=
AMAZON_API_HOST=
```

Keep all real credentials outside the source code. Do not commit `.env` files, API keys, SMTP passwords, or production secrets to GitHub.

## Project Context

BrokersHub was developed as a collaborative full-stack project. My role included team leadership, task coordination, architecture input, and hands-on development of important customer and broker workflows.

The project focuses on more than listing brokers. It demonstrates how role-based access, structured request management, external APIs, AI-assisted search, and customer feedback can work together in one practical Django application.

## Current Status

The project is under active development.

The current version demonstrates:

- Customer and broker authentication flows.
- Broker discovery and filtering.
- Request and quotation management.
- Deal status tracking.
- AI-assisted product discovery.
- Broker reviews and rating calculations.
- Email-based contact handling.

Future improvements include automated testing, production-ready environment configuration, stronger deployment settings, and expanded broker management tools.

## Author

**Karim Jaber**

Full-Stack Developer focused on Python, Django, practical workflow systems, and user-centered web applications.
