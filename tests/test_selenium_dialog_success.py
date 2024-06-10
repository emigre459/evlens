from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

URL = "https://www.plugshare.com/location/10000"
DRIVER = webdriver.Chrome()

# Add a cookie to the browser that indicates that the user has not consented to cookies
# driver.add_cookie({"name": "consent", "value": "false"})

def reject_cookies(driver, url):
    """Rejects cookies on a website using Selenium.

    Args:
        driver: The Selenium WebDriver instance.
        url: The URL of the website to access.

    Returns:
        True if cookies were rejected successfully, False otherwise.
    """

    driver.get(url)

    try:
        # Wait for the cookie banner
        wait = WebDriverWait(driver, 10)
        cookie_banner = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "mini-bar-mobile")))

        # Scroll to the cookie banner to activate Manage Settings link
        driver.execute_script("arguments[0].scrollIntoView();", cookie_banner)

        # Optionally click on the banner to trigger the "Manage Settings" link
        # cookie_banner.click()

        # Wait for the "Manage Settings" link to appear
        manage_settings_link = wait.until(EC.visibility_of_element_located((By.LINK_TEXT, "Manage Settings")))

        # Click the link
        manage_settings_link.click()

        # ... your code to handle the cookie settings page ...

        return True

    except (NoSuchElementException, TimeoutException):
        print("Cookie banner or 'Manage Settings' link not found. Assuming cookies are not rejected.")
        return False

    except Exception as e:
        print(f"Unknown rror rejecting cookies: {e}")
        return False

# Example usage
assert reject_cookies(DRIVER, URL), "Error rejecting cookies."
DRIVER.get(URL)

# Refresh the page to see the "Manage Settings" link
# driver.refresh()

print("SUCCESS!")