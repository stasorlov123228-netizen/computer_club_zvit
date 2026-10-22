from django.middleware.csrf import CsrfViewMiddleware


class PaymentCsrfMiddleware(CsrfViewMiddleware):
    """Retain the historical middleware path with standard Django checks."""
