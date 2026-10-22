import os
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


BASE_URL = "http://127.0.0.1:8000"
HOME_URL = f"{BASE_URL}/"
LOGIN_URL = f"{BASE_URL}/login/"
ACCOUNT_URL = f"{BASE_URL}/account/"
TEST_USERNAME = "test_user2"
WAIT_SECONDS = 12


@pytest.fixture
def browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1440,1000")
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(20)
        yield driver
    finally:
        driver.quit()


@pytest.fixture
def existing_user_password():
    password = os.environ.get("TEST_USER_PASSWORD")
    if not password:
        pytest.fail(
            "Не задано TEST_USER_PASSWORD. Установіть змінну середовища для "
            "існуючого test_user2; значення пароля не виводиться й не зберігається у файлі."
        )
    return password


def test_homepage_loads_with_expected_content_and_navigation(browser):
    try:
        with urlopen(HOME_URL, timeout=5) as response:
            assert response.status == 200, "Головна сторінка повернула не HTTP 200."
            assert response.geturl() == HOME_URL, "HTTP-запит перейшов на неочікувану адресу."
    except URLError:
        pytest.fail(
            "Не вдалося перевірити HTTP-відповідь. Переконайтеся, що Django-сервер "
            "працює на 127.0.0.1:8000."
        )

    browser.get(HOME_URL)
    wait = WebDriverWait(browser, WAIT_SECONDS)
    main = wait.until(EC.visibility_of_element_located((By.ID, "main-content")))
    heading = wait.until(EC.visibility_of_element_located((By.ID, "hero-title")))
    navigation = wait.until(EC.visibility_of_element_located((By.ID, "main-nav")))

    wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
    assert browser.current_url == HOME_URL, "Браузер залишив головну сторінку."
    assert browser.title.startswith("Lviv Arena"), "Заголовок вкладки не відповідає сайту."
    assert "LVIV" in heading.text and "ARENA" in heading.text
    assert browser.find_element(
        By.CSS_SELECTOR, "header.main-header a.logo[href='#home']"
    ).is_displayed()
    assert main.find_element(By.CSS_SELECTOR, ".hero-description").is_displayed()
    assert navigation.find_element(By.CSS_SELECTOR, "a[href='/clubs/']").is_displayed()
    assert navigation.find_element(By.CSS_SELECTOR, "a[href='/news/']").is_displayed()
    assert navigation.find_element(By.CSS_SELECTOR, "a[href='/tournaments/']").is_displayed()
    assert navigation.find_element(By.CSS_SELECTOR, "a.booking-link[href='/booking/']").is_displayed()
    assert navigation.find_element(By.CSS_SELECTOR, "a.account-link[href='/login/']").is_displayed()

    feature_heading = (By.CSS_SELECTOR, ".feature-grid .feature-card h3")
    browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        main.find_element(By.CSS_SELECTOR, ".feature-grid"),
    )
    assert wait.until(EC.visibility_of_element_located(feature_heading)).is_displayed()

    tariff_heading = (By.CSS_SELECTOR, "#prices .tariff-grid .tariff-card h3")
    browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        main.find_element(By.ID, "prices"),
    )
    assert wait.until(EC.visibility_of_element_located(tariff_heading)).is_displayed()
    assert not any(
        marker in browser.page_source.lower()
        for marker in ("traceback (most recent call last)", "django.core.exceptions")
    ), "Замість головної сторінки відобразилася помилка Django."


def test_existing_user_can_login_and_open_account(existing_user_password, browser):
    browser.get(HOME_URL)
    wait = WebDriverWait(browser, WAIT_SECONDS)

    login_link = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.account-link[href='/login/']"))
    )
    login_link.click()
    username_input = wait.until(EC.visibility_of_element_located((By.NAME, "username")))
    password_input = wait.until(EC.visibility_of_element_located((By.NAME, "password")))
    username_input.send_keys(TEST_USERNAME)
    password_input.send_keys(existing_user_password)
    browser.find_element(By.CSS_SELECTOR, "form.auth-form button[type='submit']").click()

    try:
        wait.until(EC.url_to_be(HOME_URL))
    except TimeoutException as error:
        if browser.current_url.rstrip("/") == LOGIN_URL.rstrip("/"):
            raise AssertionError(
                "Авторизація test_user2 неуспішна. Перевірте TEST_USER_PASSWORD "
                "та стан наявного облікового запису; пароль не виводиться."
            ) from error
        raise AssertionError(
            "Після надсилання форми не відбувся очікуваний перехід на головну сторінку."
        ) from error

    account_link = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.account-link[href='/account/']"))
    )
    account_link.click()
    wait.until(EC.url_to_be(ACCOUNT_URL))
    account_heading = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, ".profile h2"))
    )
    assert account_heading.text == TEST_USERNAME, (
        "У профілі відображається не обліковий запис test_user2."
    )
