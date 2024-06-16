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
DRIVER.maximize_window()


# Add a cookie to the browser that indicates that the user has not consented to cookies
# driver.add_cookie({"name": "consent", "value": "false"})

def interact_with_cookies(driver, url, reject_cookies: bool = True):
    """Rejects cookies on a website using Selenium.

    Args:
        driver: The Selenium WebDriver instance.
        url: The URL of the website to access.

    Returns:
        True if cookies were rejected successfully, False otherwise.
    """

    driver.get(url)

    try:
        wait = WebDriverWait(driver, 5)

        # Wait for the cookie dialog to appear
        iframe = wait.until(EC.visibility_of_element_located((
            By.ID,
            "global-consent-notice"
        )))
        
        logger.info("Found the banner!")
        
        # Select default content so we can switch to cookie iframe
        # Adapted from https://stackoverflow.com/a/21476147
        # Pull out of main page frame so we can select a different frame (cookies)
        logger.info("Switching to cookie dialog iframe...")
        driver.switch_to.frame(iframe)
        
        if reject_cookies:
            logger.info("Rejecting cookies...")
            
            logger.info("Selecting 'Manage Settings' link...")
            manage_settings_link = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "/html/body/app-root/app-theme/div/div/app-notice/app-theme/div/div/app-home/div/div[2]/app-footer/div/div/app-section-links/span/a"
            )))
            manage_settings_link.click()
            
            logger.info("Clicking 'Reject All' button...")
            reject_all_button = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//*[@id=\"denyAll\"]"
            )))
            reject_all_button.click()
            
            logger.info("Confirming rejection...")
            reject_all_button_confirm = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//*[@id=\"mat-dialog-0\"]/ng-component/app-theme/div/div/div[2]/button[2]"
            )))
            reject_all_button_confirm.click()
            
        else:
            logger.info("Accepting cookies...")
            accept_button = driver.find_element(By.TAG_NAME, "button")
            accept_button.click()
        
        
        
        # Switch back to main frame
        logger.info("Switching back to main page content...")
        driver.switch_to.default_content()
        

        return True

    except (NoSuchElementException, TimeoutException) as e1:
        logger.error("Cookie banner or 'Manage Settings' link not found. Assuming cookies are not rejected.")
        raise e1

    except Exception as e2:
        logger.error(f"Unknown error rejecting cookies: {e2}")

if __name__ == '__main__':
    # Example usage
    logger.info("Starting cookie dialog test...")
    assert interact_with_cookies(DRIVER, URL, reject_cookies=True), "Error rejecting cookies."

    # Refresh the page to see the "Manage Settings" link
    # driver.refresh()

    logger.info("SUCCESS!")

    # Ultimately flow using this code should be:
    # 1. Check if banner is present via try-except on timeout
    # 2. If present, go through rejection logic then exit login dialog
    # 3. If missing, proceed with exiting login dialog directly