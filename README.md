# Lviv Arena - система керування комп’ютерним клубом

Django-застосунок для комп’ютерного клубу: публічні сторінки, бронювання комп’ютерів, тарифи, облікові записи, оплата та адміністративна панель. Проєкт містить застосунок `club`, конфігурацію Django в `config`, шаблони й статичні ресурси в `club/templates` та `club/static`, а схему бази даних - у `club/migrations`.

## Вимоги

Потрібні Python 3.13 або сумісніша версія та MySQL 8.4 (у середовищі розробки перевірено MySQL 8.4.11). Робоча конфігурація використовує базу `computer_club`, адресу `127.0.0.1` і порт `3302`; пароль задається лише локально в `.env`. Для `mysqlclient` у Windows можуть знадобитися інструменти збірки. Точні версії Python-залежностей наведені в `requirements.txt`.

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
DJANGO_SECURE_SSL_REDIRECT=False
MYSQL_DATABASE=computer_club
MYSQL_USER=computer_club_app
MYSQL_PASSWORD=пароль
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3302
```

Для робочого середовища вимкніть `DJANGO_DEBUG`, задайте надійний `DJANGO_SECRET_KEY`, точні дозволені хости й HTTPS trusted origins. Не додавайте `.env` до Git.
`MYSQL_USER` і непорожній `MYSQL_PASSWORD` є обов’язковими параметрами; застосунок більше не підставляє `root` або порожній пароль автоматично. Використовуйте окремого користувача MySQL із мінімально потрібними правами.

## MySQL і міграції

Створіть у MySQL базу даних `computer_club` із кодуванням `utf8mb4` і надайте окремому користувачу застосунку потрібні права на цю базу. Наприклад, адміністратор MySQL може створити локального користувача й надати доступ (замініть пароль локально, не додавайте його до Git):

```sql
CREATE DATABASE computer_club CHARACTER SET utf8mb4;
CREATE USER 'computer_club_app'@'127.0.0.1' IDENTIFIED BY 'set-a-local-password';
GRANT ALL PRIVILEGES ON computer_club.* TO 'computer_club_app'@'127.0.0.1';
```

Після налаштування `.env` застосуйте міграції:

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

## Tests and checks

The fast Django tests in `club/tests.py` cover pricing, booking status, and tariff-to-computer mapping. The Selenium suite implements two documented test cases: TC-01 checks the homepage and TC-02 covers login and opening the account page.

Run the site in one terminal:

```powershell
python manage.py runserver
```

Both tests read `TEST_USER_USERNAME` and `TEST_USER_PASSWORD` from the ignored local `.env` file. In a second PowerShell terminal, activate the virtual environment and run them; Chrome is visible by default:

```powershell
.\venv\Scripts\Activate.ps1
python -m pytest ui_tests/test_site_ui.py -v -s
```

Set `TEST_HEADLESS=1` to run without showing the Chrome window. Each test opens and closes its own browser session. Chrome and a compatible ChromeDriver are required.

Django checks:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The Django test runner needs MySQL access and permission to create and remove its test database. Use a test database account with those permissions.
## Основні можливості та оплата

Клієнт може зареєструватися, переглядати комп’ютери й тарифи, створювати та переглядати власні бронювання. Персонал керує бронюваннями та каталогом через адміністративні сторінки й Django Admin.

Форма оплати карткою є локальною демонстрацією: сервер перевіряє формат реквізитів і стан бронювання, але платіжний шлюз не підключений і кошти не списуються. Не вводьте справжні карткові реквізити. Номер картки, CVC/CVV і строк дії не зберігаються як платіжні дані.

## Демонстраційні дані

Створіть демонстраційні тарифи та комп’ютери командою:

```powershell
python manage.py seed_demo_data
```

Команда додає відсутні записи каталогу та одне майбутнє гостьове бронювання для `Demo Customer`.
