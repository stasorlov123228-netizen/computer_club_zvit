import os

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
WAIT_SECONDS = 12


@pytest.fixture
def browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1440,1000")
    if os.environ.get("TEST_HEADLESS", "1").strip().lower() in {"1", "true", "yes"}:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)
    try:
        yield driver
    finally:
        driver.quit()


def test_tc01_homepage_loads_and_shows_main_content(browser):
    """TC-01: homepage, navigation, information sections, and tariffs render."""
    wait = WebDriverWait(browser, WAIT_SECONDS)
    home_url = f"{BASE_URL}/"
    browser.get(home_url)

    main = wait.until(EC.visibility_of_element_located((By.ID, "main-content")))
    heading = wait.until(EC.visibility_of_element_located((By.ID, "hero-title")))
    navigation = wait.until(EC.visibility_of_element_located((By.ID, "main-nav")))

    assert browser.current_url == home_url
    assert browser.title.startswith("Lviv Arena")
    assert "LVIV" in heading.text and "ARENA" in heading.text

    expected_links = (
        "/clubs/",
        "/news/",
        "/tournaments/",
        "/booking/",
        "/login/",
    )
    for href in expected_links:
        link = navigation.find_element(By.CSS_SELECTOR, f"a[href='{href}']")
        assert link.is_displayed(), f"Expected visible navigation link: {href}"

    feature_grid = main.find_element(By.CSS_SELECTOR, ".feature-grid")
    browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", feature_grid,
    )
    feature_cards = feature_grid.find_elements(By.CSS_SELECTOR, ".feature-card h3")
    assert feature_cards, "Homepage information cards are missing."
    assert any(card.is_displayed() for card in feature_cards)

    pricing = main.find_element(By.ID, "prices")
    browser.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});", pricing,
    )
    tariff_cards = pricing.find_elements(By.CSS_SELECTOR, ".tariff-grid .tariff-card h3")
    assert len(tariff_cards) >= 4, "Expected the four club tariffs to be shown."
    assert all(card.is_displayed() for card in tariff_cards)

    error_markers = (
        "traceback (most recent call last)",
        "django.core.exceptions",
        "internal server error",
    )
    assert not any(marker in browser.page_source.lower() for marker in error_markers), (
        "A Django error page was rendered instead of the homepage."
    )


def test_tc02_registered_user_can_login_and_open_account(browser):
    """TC-02: a registered user logs in and sees their personal account."""
    username = os.environ.get("TEST_USER_USERNAME", "")
    password = os.environ.get("TEST_USER_PASSWORD", "")
    if not username or not password:
        pytest.fail(
            "Set TEST_USER_USERNAME and TEST_USER_PASSWORD for an existing test account."
        )

    wait = WebDriverWait(browser, WAIT_SECONDS)
    home_url = f"{BASE_URL}/"
    browser.get(home_url)

    login_link = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.account-link[href='/login/']"))
    )
    login_link.click()
    wait.until(EC.visibility_of_element_located((By.NAME, "username"))).send_keys(username)
    browser.find_element(By.NAME, "password").send_keys(password)
    browser.find_element(By.CSS_SELECTOR, "form.auth-form button[type='submit']").click()

    wait.until(EC.url_to_be(home_url))
    account_link = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.account-link[href='/account/']"))
    )
    account_link.click()
    wait.until(EC.url_to_be(f"{BASE_URL}/account/"))

    account_heading = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, ".profile h2"))
    )
    assert account_heading.text == username, (
        f"Expected account heading {username!r}, got {account_heading.text!r}."
    )
