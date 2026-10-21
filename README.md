# Lviv Arena — система керування комп’ютерним клубом

Django-застосунок для комп’ютерного клубу: публічні сторінки, бронювання комп’ютерів, тарифи, облікові записи, оплата та адміністративна панель. Проєкт містить застосунок `club`, конфігурацію Django в `config`, шаблони й статичні ресурси в `club/templates` та `club/static`, а схему бази даних — у `club/migrations`.

## Вимоги

Потрібні Python 3.13.14 (версія середовища розробки), MySQL 8.4.11 (перевірена версія сервера) та інструменти збірки для встановлення `mysqlclient` у Windows за потреби. Точні версії Python-залежностей наведені в `requirements.txt` за фактичним `pip freeze` віртуального середовища.

## Встановлення

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Налаштування середовища

Скопіюйте `.env.example` у `.env` і задайте власний секретний ключ та параметри MySQL:

```text
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=унікальний-випадковий-секрет
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=
MYSQL_DATABASE=computer_club
MYSQL_USER=root
MYSQL_PASSWORD=пароль
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3302
```

Для робочого середовища вимкніть `DJANGO_DEBUG`, задайте надійний `DJANGO_SECRET_KEY`, точні дозволені хости й HTTPS trusted origins. Не додавайте `.env` до Git.

## MySQL і міграції

Створіть у MySQL базу даних `computer_club` із кодуванням `utf8mb4` і переконайтеся, що вказаний користувач має до неї доступ. Потім виконайте:

```powershell
python manage.py migrate
```

Переглянути заплановані міграції без застосування можна командою `python manage.py migrate --plan`.

## Запуск

```powershell
python manage.py createsuperuser
python manage.py runserver
```

Відкрийте `http://127.0.0.1:8000/`. Адміністративна панель Django доступна за адресою `/admin/`.

## Тести та перевірки

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Тестам потрібен доступний MySQL і право створювати та видаляти тимчасову тестову базу.

## Демонстраційні дані

Створіть демонстраційні тарифи та комп’ютери командою:

```powershell
python manage.py seed_demo_data
```

Команда додає лише відсутні записи каталогу, безпечно працює при повторному запуску й не змінює користувачів або бронювання. Перевірені власні фікстури можна завантажити через `python manage.py loaddata <fixture.json>`.
