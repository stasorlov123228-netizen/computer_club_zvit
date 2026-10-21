from django.views.generic import DetailView, ListView

from ..models import Tariff


class TariffListView(ListView):
    model = Tariff
    template_name = 'club/tariff_list.html'
    context_object_name = 'tariffs'
    queryset = Tariff.objects.order_by('price_per_hour', 'name')


class TariffDetailView(DetailView):
    model = Tariff
    template_name = 'club/tariff_detail.html'
    context_object_name = 'tariff'
