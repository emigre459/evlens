from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

URL = "https://www.plugshare.com/location/10000"
DRIVER = webdriver.Chrome()

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

    driver.get(url)

    try:
        # Wait for the exit button
        wait = WebDriverWait(driver, 10)
        esc_button = wait.until(EC.visibility_of_element_located((
            By.XPATH,
            # "//*[@id=\"dialogContent_authenticate\"]/button/md-icon" # old
            "//*[@id=\"dialogContent_authenticate\"]/button" # from chrome
        )))
        esc_button.click()

        # ... your code to handle the cookie settings page ...

        return True

    except (NoSuchElementException, TimeoutException):
        print("Login dialog exit button not found.")
        return False

    except Exception as e:
        print(f"Unknown error trying to exit login dialog: {e}")
        return False

# Example usage
assert exit_login(DRIVER, URL), "Error exiting loging dialog"
# DRIVER.get(URL)

# Refresh the page to see the "Manage Settings" link
# driver.refresh()

print("SUCCESS!")