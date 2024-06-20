import time
from tqdm import tqdm
import pandas as pd
import numpy as np
import os
import re
from typing import Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement

from evlens.logs import setup_logger
logger = setup_logger(__name__)


class CheckIn:
    '''
    Tracks all the different components of a single check-in and can return as a single-row pandas DataFrame to be used elsewhere.
    '''
    def __init__(self, checkin_element: WebElement):
        self.element = checkin_element
        
    def parse(self) -> pd.DataFrame:
        '''
        Parses the checkin_element provided during instantiation and returns
        the info found.

        Returns
        -------
        pd.DataFrame
            Single-row DataFrame providing the data comprising the check-in
        '''
        output = dict()
        
        # Details part
        try:
            details_element = self.element.find_element(By.CLASS_NAME, "details")
            details_children = details_element.find_elements(By.XPATH, "./child::*")
            for d in details_children:
                if d.get_attribute("class") == 'date ng-binding':
                    output['date'] = pd.to_datetime(d.text)
                elif d.get_attribute("class") == 'car ng-binding':
                    output['car'] = d.text
                elif d.get_attribute("class") == 'additional':
                    self.additional_children = d.find_elements(By.XPATH, "./child::*")
            
            # "Additional" part
            for d in self.additional_children:
                if d.get_attribute("class") == 'problem ng-scope':
                    output['problem'] = d.text
                elif d.get_attribute("class") == 'connector ng-binding':
                    output['connector_type'] = d.text
                elif d.get_attribute("class") == 'kilowatts ng-scope':
                    output['charge_power_kilowatts'] = d.text
                elif d.get_attribute("class") == 'comment ng-binding':
                    output['comment'] = d.text
                    
        except NoSuchElementException:
            logger.debug("Checkin entry blank/not found")
                
        
        # Check what columns we're missing and fill with null
        expected_columns = [
            'date',
            'car',
            'problem',
            'connector_type',
            'charge_power_kilowatts',
            'comment'
        ]
        for c in expected_columns:
            if c not in output.keys():
                output[c] = np.nan
        
        
        # Drop anything that is all-nulls when ignoring location_id
        return pd.DataFrame(output, index=[0]).dropna(how='all')


class Scraper:

    def __init__(
        self,
        save_filepath: str,
        save_every: int = 100,
        timeout: int = 3,
        page_load_pause: int = 1,
        headless: bool = True
    ):
        self.timeout = timeout
        self.save_path = save_filepath
        self.save_every = save_every
        self.page_load_pause = page_load_pause
        
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
            self.driver.save_screenshot("selenium_login_not_found.png")

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
    
    
    #TODO: clean up and try to more elegantly extract things en masse
    #TODO: use fewer attributes for data maintenance
    def scrape_location(self, location_id: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        '''
        Scrapes a single location (single webpage)

        Returns
        -------
        Tuple[pd.DataFrame, pd.DataFrame]
            (Single-row dataframe with location metadata, dataframe with one row per check-in comment)
        '''
        output = dict()
        
        logger.info("Starting page scrape...")
        try: ## FIND STATION NAME
            output['name'] = self.wait.until(EC.visibility_of_element_located((
                By.XPATH,
                "//*[@id=\"display-name\"]/div/h1"
            ))).text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station name error, skipping...")
            return
        
        try: ## FIND STATION ADDRESS
            
            output['address'] = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station address error", exc_info=True)
            output['address'] = np.nan
        
        try: ## FIND STATION RATING
            
            output['plugscore'] = self.driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station rating error", exc_info=True)
            output['plugscore'] = np.nan

        try: ## FIND STATION WATTAGE
            
            output['wattage'] = self.driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Wattage error", exc_info=True)
            output['wattage'] = np.nan
            
        try: ## FIND STATION HOURS
            
            output['service_hours'] = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station hours error", exc_info=True)
            output['service_hours'] = np.nan

        try: # Get total check-in counts
            def _get_checkin_count(text):
                match = re.search(r"\(\s*(\d+)\s*\)", text)
                if match:
                    return int(match.group(1))
                return np.nan
            
            checkins = self.driver.find_element(
                By.XPATH,
                "//*[@id=\"checkins\"]"
                ).text
            output['checkin_count'] = _get_checkin_count(checkins)
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Check-in count error", exc_info=True)
            output['checkin_count'] = np.nan

        try: # PULL IN COMMENT TEXT
            more_comments_link = self.driver.find_element(
                By.XPATH,
                "//*[@id=\"checkins\"]/div[2]/span[3]"
            )
            more_comments_link.click()
            
            detailed_checkins = self.driver.find_element(
                By.XPATH,
                "//*[@id=\"dialogContent_reviews\"]/div/div"
            ).find_elements(By.XPATH, "./child::*")
            
            self.detailed_checkins = detailed_checkins
            
            checkin_dfs = []
            for checkin in tqdm(detailed_checkins, desc="Parsing checkins for location"):
                c = CheckIn(checkin)
                out = c.parse()
                if not out.empty:
                    checkin_dfs.append(out)
                
            df_checkins = pd.concat(checkin_dfs, ignore_index=True)
            df_checkins['location_id'] = location_id
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Comments error", exc_info=True)
            
        logger.info("Page scrape complete!")
        df_location = pd.DataFrame(output, index=[0])
        df_location['id'] = location_id
        
        return (
            df_location,
            df_checkins
        )
        
    #TODO: add in saving to disk at X pages (pickle for now)
    def run(self, start_location, end_location):
        logger.info("Beginning scraping!")

        all_locations = []
        all_checkins = []
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
            df_location, df_checkins = self.scrape_location(location_id)
            all_locations.append(df_location)
            all_checkins.append(df_checkins)
            
            if i+1 % self.save_every == 0:
                logger.info(f"Saving checkpoint at location {i}")
                
                path = self.save_path + f"df_locations_{i}.pkl"
                pd.concat(all_locations, ignore_index=True).to_pickle(path)
                
                path = self.save_path + f"df_checkins_{i}.pkl"
                pd.concat(all_checkins, ignore_index=True).to_pickle(path)

            #TODO: tune between page switches
            logger.info(f"Sleeping for {self.page_load_pause} seconds")
            time.sleep(self.page_load_pause)

        self.driver.quit()
        
        #TODO: add station location integers as column
        df_all_locations = pd.concat(all_locations, ignore_index=True)
        df_all_locations.to_pickle(self.save_path + f"df_all_locations.pkl")
        
        df_all_checkins = pd.concat(all_checkins, ignore_index=True)
        df_all_checkins.to_pickle(self.save_path + f"df_all_checkins.pkl")
        
        logger.info("Scraping complete!")
        return df_all_locations, df_all_checkins