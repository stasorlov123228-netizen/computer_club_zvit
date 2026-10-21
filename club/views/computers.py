from django.views.generic import DetailView, ListView

from ..models import Computer


class ComputerListView(ListView):
    model = Computer
    template_name = 'club/computer_list.html'
    context_object_name = 'computers'
    queryset = Computer.objects.order_by('name')


class ComputerDetailView(DetailView):
    model = Computer
    template_name = 'club/computer_detail.html'
    context_object_name = 'computer'
