from django.middleware.csrf import CsrfViewMiddleware


class PaymentCsrfMiddleware(CsrfViewMiddleware):
    def _origin_verified(self, request):
        resolver_match = getattr(request, 'resolver_match', None)
        if (
            request.method == 'POST'
            and request.META.get('HTTP_ORIGIN') == 'null'
            and resolver_match
            and resolver_match.url_name == 'payment_result'
        ):
            return True
        return super()._origin_verified(request)
