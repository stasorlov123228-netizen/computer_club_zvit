# Lviv Arena — система керування комп’ютерним клубом

Django-застосунок для комп’ютерного клубу: публічні сторінки, бронювання комп’ютерів, тарифи, облікові записи, оплата та адміністративна панель. Проєкт містить застосунок `club`, конфігурацію Django в `config`, шаблони й статичні ресурси в `club/templates` та `club/static`, а схему бази даних — у `club/migrations`.

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

## Тести та перевірки

Перевірені версії `pytest` і `selenium` також зафіксовані в `requirements.txt`.
Для Selenium UI-тестів потрібен запущений сайт, Chrome та доступний ChromeDriver
(Selenium Manager може знайти драйвер автоматично). Авторизаційний тест очікує
вже наявний обліковий запис `test_user2`; пароль передається лише через змінну
оточення, не зберігається у файлах:

```powershell
python manage.py runserver
```

В іншому терміналі з активованим тим самим віртуальним середовищем задайте
пароль прихованим вводом і виконайте:

```powershell
$securePassword = Read-Host -AsSecureString "Пароль test_user2"
$env:TEST_USER_PASSWORD = [System.Net.NetworkCredential]::new('', $securePassword).Password
python -m pytest ui_tests/test_site_ui.py -v
Remove-Item Env:TEST_USER_PASSWORD
```

UI-тест входить у наявний обліковий запис і створює звичайну веб-сесію, тому
запускайте його лише з тестовою базою та тестовим обліковим записом. Команда
вище очищає змінну середовища після проходження тесту.

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Тестовому runner Django потрібен доступний MySQL і право створювати та видаляти
окрему тестову базу. Не запускайте його з обліковими даними робочої БД, якщо
такі права створять ризик для даних. У поточній копії окремих модулів тестів
Django немає; наведені команди `check` і перевірки міграцій можна виконувати
без створення тестових записів.

## Основні можливості та оплата

Клієнт може зареєструватися, переглядати комп’ютери й тарифи, створювати та переглядати власні бронювання. Персонал керує бронюваннями та каталогом через адміністративні сторінки й Django Admin.

Форма оплати карткою є локальною демонстрацією: сервер перевіряє формат реквізитів і стан бронювання, але платіжний шлюз не підключений і кошти не списуються. Не вводьте справжні карткові реквізити. Номер картки, CVC/CVV і строк дії не зберігаються як платіжні дані.

## Демонстраційні дані

Створіть демонстраційні тарифи та комп’ютери командою:

```powershell
python manage.py seed_demo_data
```

Команда додає лише відсутні записи каталогу, безпечно працює при повторному запуску й не змінює користувачів або бронювання. Перевірені власні фікстури можна завантажити через `python manage.py loaddata <fixture.json>`.
