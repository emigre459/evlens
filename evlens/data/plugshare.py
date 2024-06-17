import time
from tqdm import tqdm
import pandas as pd
import numpy as np
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from evlens.logs import setup_logger
logger = setup_logger(__name__)

class Scraper:

    def __init__(
        self,
        save_filepath: str,
        save_every: int = 100,
        timeout: int = 3,
        headless: bool = True
    ):
        self.timeout = timeout
        self.save_path = save_filepath
        self.save_every = save_every
        
        if not os.path.exists(self.save_path):
            logger.warning("Save filpath does not exist, creating it...")
            os.makedirs(self.save_path)
        
        self.chrome_options = Options()
        
        # Removes automation infobar
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Run without window open
        if headless:
            self.chrome_options.add_argument('--headless=new')
        
        # Get rid of kruft that will slow us down
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-notifications")
        
        # Turn off geolocation to speed things up
        self.prefs = {"profile.default_content_setting_values.geolocation":2} 
        self.chrome_options.add_experimental_option("prefs", self.prefs)
        
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.wait = WebDriverWait(self.driver, self.timeout)
        
        #TODO: get rid of these through refactor
        self.locationlist = []
        self.all_stations = []
        
    def exit_login_dialog(self):
        logger.info("Attempting to exit login dialog...")
        try:
            # Wait for the exit button
            esc_button = self.wait.until(EC.visibility_of_element_located((
                By.XPATH,
                "//*[@id=\"dialogContent_authenticate\"]/button"
            )))
            esc_button.click()
            logger.info("Successfully exited the login dialog!")

        except (NoSuchElementException, TimeoutException):
            logger.error("Login dialog exit button not found.")

        except Exception as e:
            raise RuntimeError(f"Unknown error trying to exit login dialog: {e}")

    #TODO: make logger.info into logger.debug everywhere?
    def reject_all_cookies_dialog(self):
        # Wait for the cookie dialog to appear
        iframe = self.wait.until(EC.visibility_of_element_located((
            By.ID,
            "global-consent-notice"
        )))        
        logger.info("Found the cookie banner!")
        
        # Adapted from https://stackoverflow.com/a/21476147
        # Pull out of main page frame so we can select a different frame (cookies)
        logger.info("Switching to cookie dialog iframe...")
        self.driver.switch_to.frame(iframe)
        
        logger.info("Selecting 'Manage Settings' link...")
        manage_settings_link = self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "/html/body/app-root/app-theme/div/div/app-notice/app-theme/div/div/app-home/div/div[2]/app-footer/div/div/app-section-links/span/a"
        )))
        manage_settings_link.click()
        
        logger.info("Clicking 'Reject All' button...")
        reject_all_button = self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//*[@id=\"denyAll\"]"
        )))
        reject_all_button.click()
        
        logger.info("Confirming rejection...")
        reject_all_button_confirm = self.wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//*[@id=\"mat-dialog-0\"]/ng-component/app-theme/div/div/div[2]/button[2]"
        )))
        reject_all_button_confirm.click()
        
        # Switch back to main frame
        logger.info("Switching back to main page content...")
        self.driver.switch_to.default_content()
    
    
    #TODO: figure out exact exceptions being seen and catch them less broadly
    #TODO: clean up and try to more elegantly extract things en masse
    #TODO: use fewer attributes for data maintenance
    def scrape_location(self):
        logger.info("Starting page scrape...")
        try: ## FIND STATION NAME
            self.wait.until(EC.visibility_of_element_located((
                By.XPATH,
                "//*[@id=\"display-name\"]/div/h1"
            )))
            self.name = self.driver.find_element(
                By.XPATH,
                "//*[@id=\"display-name\"]/div/h1"
                ).text
        except:
            logger.error("Station name error", exc_info=True)
            self.name = np.nan
        
        try: ## FIND STATION ADDRESS
            
            self.address = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
        except:
            logger.error("Station address error", exc_info=True)
            self.address = np.nan
        
        try: ## FIND STATION RATING
            
            self.rating = self.driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
        except:
            logger.error("Station rating error", exc_info=True)
            self.rating = np.nan

        try: ## FIND STATION WATTAGE
            
            self.wattage = self.driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
        except:
            logger.error("Wattage error", exc_info=True)
            self.wattage = np.nan
            
        try: ## FIND STATION HOURS
            
            self.hours = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
        except:
            logger.error("Station hours error", exc_info=True)
            self.hours = np.nan

        try: # FIND CHECKINS 
            
            self.checkins = self.driver.find_element(By.XPATH, "//*[@id=\"checkins\"]").text
            self.checkins = self.checkins.split(' ')[1].split('\n')[0]
            #checkins = checkins.split('\n')[0]
        except:
            logger.error("Check-ins error", exc_info=True)

        try: # FIND COMMENTS
            
            self.commentList = []
            self.comments = self.driver.find_elements(By.CLASS_NAME, "details")
            for comment in self.comments:
                self.commentList.append(comment.text)
             
            for comment in self.commentList:
                comment.replace("check_circle", "")
            self.finalComments = ', '.join(self.commentList)
        except:
            logger.error("Comments error", exc_info=True)
            
        try: # SCRAPE CAR
            
            carList = []
            self.cars = self.driver.find_elements(By.CLASS_NAME, "car ng-binding") # PRINTS TYPE OF CAR FOR EACH PERSON
            for car in self.cars:
                carList.append(car)
            self.cars = ', '.join(carList)
        except:
            logger.error("Car details error", exc_info=True)
            
        try: # PUT ALL TOGETHER
            
            self.all_stations.append({"Name": self.name, "Address": self.address, "Rating": self.rating, "Wattage": self.wattage, "Hours": self.hours, "Checkins": self.checkins, "Comments": self.finalComments, "Car": self.cars})
        except:
            logger.error("Data append error", exc_info=True)
            
        logger.info("Page scrape complete!")
        
    #TODO: add in saving to disk at X pages (pickle for now)
    def run(self, start_location, end_location):
        logger.info("Beginning scraping!")

        for i, location_id in enumerate(tqdm(
            range(start_location, end_location+1),
            desc="Parsing stations"
        )):
            self.locationlist.append(location_id)
            url = f"https://www.plugshare.com/location/{location_id}"
            self.driver.get(url)
            
            # Have to maximize to see all links...weirdly
            self.driver.maximize_window()

            try:
                self.reject_all_cookies_dialog()
                
            except (NoSuchElementException, TimeoutException) as e_cookies:
                logger.error("Cookie banner or 'Manage Settings' link not found. Assuming cookies are not rejected.")
                
            # TODO: try-except here
            self.exit_login_dialog()
            self.scrape_location()
            
            if i+1 % self.save_every == 0:
                logger.info(f"Saving checkpoint at location {i}")
                path = self.save_path + f"{i}.pkl"
                pd.DataFrame(self.all_stations).to_pickle(path)

            #TODO: tune between page switches
            wait_between_loads = 5
            logger.info(f"Sleeping for {wait_between_loads} seconds")
            time.sleep(wait_between_loads)

        self.driver.quit()
        
        #TODO: add station location integers as column
        df = pd.DataFrame(self.all_stations)
        df.to_pickle(self.save_path + f"all_data.pkl")
        logger.info("Scraping complete!")
        return df