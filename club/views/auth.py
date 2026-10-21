from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import CustomUserCreationForm
from ..phone_numbers import PHONE_COUNTRIES

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = AuthenticationForm(
        request,
        data=request.POST or None
    )

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('home')

    return render(request, 'club/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = CustomUserCreationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('home')

    return render(request, 'club/register.html', {
        'form': form,
        'phone_countries': [list(country) for country in PHONE_COUNTRIES],
    })

@require_POST
def logout_view(request):
    logout(request)
    return redirect('home')
