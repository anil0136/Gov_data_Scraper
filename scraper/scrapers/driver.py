import os
import shutil

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
except ImportError:
    webdriver = None
    ChromeService = None
    EdgeService = None
    ChromeOptions = None
    EdgeOptions = None

    class WebDriverException(Exception):
        pass


def _find_chrome_binary():
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Google", "Chrome Beta", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Google", "Chrome Beta", "Application", "chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _find_edge_binary():
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _configure_common_options(options, headless=True):
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


def _find_local_driver(name):
    driver_path = shutil.which(name)
    if driver_path:
        return driver_path

    # Check in current directory
    current_dir = os.getcwd()
    exe_path = os.path.join(current_dir, f"{name}.exe")
    if os.path.exists(exe_path):
        return exe_path

    cache_root = os.path.expanduser(r"~\.wdm\drivers")
    if os.path.isdir(cache_root):
        for root, _, files in os.walk(cache_root):
            for file in files:
                if file.lower() == f"{name}.exe":
                    return os.path.join(root, file)
    return None


def get_driver(headless=True):
    if os.environ.get("GOVSCRAPER_HTTP_ONLY", "").lower() in {"1", "true", "yes"}:
        raise WebDriverException("Browser scraping disabled by GOVSCRAPER_HTTP_ONLY.")

    if webdriver is None:
        raise WebDriverException(
            "Selenium is not installed. Install selenium, or use GOVSCRAPER_HTTP_ONLY=1 for HTTP fallback."
        )

    chrome_binary = _find_chrome_binary()
    edge_binary = _find_edge_binary()
    chrome_driver = _find_local_driver("chromedriver")
    edge_driver = _find_local_driver("msedgedriver")

    if chrome_binary and chrome_driver:
        chrome_options = _configure_common_options(ChromeOptions(), headless=headless)
        chrome_options.binary_location = chrome_binary
        try:
            driver = webdriver.Chrome(
                service=ChromeService(chrome_driver),
                options=chrome_options
            )
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except WebDriverException as exc:
            print(f"Chrome startup failed with local driver: {exc}")

    if chrome_binary:
        chrome_options = _configure_common_options(ChromeOptions(), headless=headless)
        chrome_options.binary_location = chrome_binary
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except WebDriverException as exc:
            print(f"Chrome startup failed with Selenium Manager: {exc}")

    if edge_binary and edge_driver:
        edge_options = _configure_common_options(EdgeOptions(), headless=headless)
        edge_options.binary_location = edge_binary
        try:
            driver = webdriver.Edge(
                service=EdgeService(edge_driver),
                options=edge_options
            )
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except WebDriverException as exc:
            print(f"Edge startup failed with local driver: {exc}")

    if edge_binary:
        edge_options = _configure_common_options(EdgeOptions(), headless=headless)
        edge_options.binary_location = edge_binary
        try:
            driver = webdriver.Edge(options=edge_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except WebDriverException as exc:
            print(f"Edge startup failed with Selenium Manager: {exc}")

    raise WebDriverException(
        "No usable browser driver found. Install Chrome or Edge with a matching driver, or set GOVSCRAPER_HTTP_ONLY=1."
    )
