from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options

from evlens.logs import setup_logger
logger = setup_logger(__name__)

TEST_LOCATION = 252784
URL = f"https://www.plugshare.com/location/{TEST_LOCATION}"

chrome_options = Options()
# Removes automation infobar
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

# Don't get benefits of incognito mode...
chrome_options.add_argument('--headless=new')

# Disables geolocation BUT enables cookie dialog...
prefs = {"profile.default_content_setting_values.geolocation":2}
chrome_options.add_experimental_option("prefs", prefs)
DRIVER = webdriver.Chrome(options=chrome_options)

# Add a cookie to the browser that indicates that the user has not consented to cookies
# driver.add_cookie({"name": "consent", "value": "false"})

def exit_login(driver, url):
    """Rejects cookies on a website using Selenium.

    Args:
        driver: The Selenium WebDriver instance.
        url: The URL of the website to access.

    Returns:
        True if cookies were rejected successfully, False otherwise.
    """
    logger.info("Starting test...")
    driver.get(url)

    try:
        # Wait for the exit button
        wait = WebDriverWait(driver, 1)
        esc_button = wait.until(EC.visibility_of_element_located((
            By.XPATH,
            # "//*[@id=\"dialogContent_authenticate\"]/button/md-icon" # old
            "//*[@id=\"dialogContent_authenticate\"]/button" # from chrome
        )))
        esc_button.click()

        # ... your code to handle the cookie settings page ...

        return True

    except (NoSuchElementException, TimeoutException):
        logger.error("Login dialog exit button not found.")
        return False

    except Exception as e:
        logger.error(f"Unknown error trying to exit login dialog: {e}")
        return False

# Example usage
assert exit_login(DRIVER, URL), "Error exiting loging dialog"
# DRIVER.get(URL)

# Refresh the page to see the "Manage Settings" link
# driver.refresh()

logger.info("SUCCESS!")