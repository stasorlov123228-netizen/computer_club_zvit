from django.core.exceptions import ValidationError
from django.shortcuts import render

from ..phone_numbers import PHONE_COUNTRIES, validate_phone_number

def tournaments_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'tournaments',
        'title': 'Турніри',
        'tournaments': [
            {
                'game': 'CS2',
                'name': 'Lviv Arena Cup',
                'format': '5 на 5'
            },
            {
                'game': 'Dota 2',
                'name': 'Arena Battle',
                'format': '5 на 5'
            },
            {
                'game': 'VALORANT',
                'name': 'Valorant Challenge',
                'format': '5 на 5'
            },
            {
                'game': 'World of Tanks',
                'name': 'Tank Masters',
                'format': 'Командний турнір'
            },
        ],
    })

def news_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'news',
        'title': 'Новини клубу',
        'news': [
            {
                'title': 'Lviv Arena відкриває двері!',
                'text': 'Знайомся з новим місцем для геймерів у Львові.',
                'date': '14 жовтня 2026',
            },
            {
                'title': '55 ігрових комп’ютерів',
                'text': 'Обирай Default, Pro, VIP або Stream-зону.',
                'date': '14 жовтня 2026',
            },
            {
                'title': 'Готуйся до турнірів',
                'text': 'Незабаром на сайті з’являтимуться нові змагання.',
                'date': '14 жовтня 2026',
            },
        ],
    })

def clubs_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'clubs',
        'title': 'Наші клуби',
    })

def feedback_view(request):
    return render(request, 'club/section_page.html', {
        'page_type': 'feedback',
        'title': 'Зворотний зв’язок',
    })

def partnership_view(request):
    sent = False
    error = ''
    phone_country = '+380'
    phone_local = ''

    if request.method == 'POST':
        phone_country = request.POST.get('phone_country', '').strip()
        phone_local = request.POST.get('phone_local', '').strip()
        try:
            validate_phone_number(phone_country, phone_local)
            sent = True
        except ValidationError as validation_error:
            error = ' '.join(validation_error.messages)

    return render(request, 'club/section_page.html', {
        'page_type': 'partnership',
        'title': 'Партнерство',
        'sent': sent,
        'error': error,
        'phone_country': phone_country,
        'phone_local': phone_local,
        'phone_countries': [list(country) for country in PHONE_COUNTRIES],
    })
