from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from evlens.logs import setup_logger
logger = setup_logger(__name__)

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784
URL = f"https://www.plugshare.com/location/{TEST_LOCATION}"

chrome_options = Options()
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
DRIVER = webdriver.Chrome(options=chrome_options)


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
        wait = WebDriverWait(driver, 2)

        # Wait for the cookie dialog to appear
        wait.until(EC.visibility_of_element_located((
            By.ID,
            "global-consent-tool-wrapper"
        )))
        
        # Select default content so we can switch to cookie iframe
        # Adapted from https://stackoverflow.com/a/21476147
        # Pull out of main page frame so we can select a different frame (cookies)
        driver.switch_to.default_content()
        driver.switch_to.frame(driver.find_element(By.ID, "global-consent-notice"))
        manage_settings_link = driver.find_element(By.LINK_TEXT, "Manage Settings")
        
        # Click the link
        manage_settings_link.click()
        
        
        # Switch to cookie frame
        
        
        
        # Switch back to main frame
        
        

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


# Ultimately flow using this code should be:
# 1. Check if banner is present via try-except on timeout
# 2. If present, go through rejection logic then exit login dialog
# 3. If missing, proceed with exiting login dialog directly