from time import time, sleep
from tqdm import tqdm
import pandas as pd
import numpy as np
import os
import re
from typing import Tuple, Set, Union, List
from urllib.parse import urlparse

from joblib import dump as joblib_dump

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    ElementNotInteractableException
)
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver import ActionChains

from evlens import get_current_datetime
from evlens.logs import setup_logger
logger = setup_logger(__name__)


ALLOWABLE_PLUG_TYPES = [
    # 'Tesla Supercharger',
    'SAE Combo DC CCS',
    # 'J-1772'
]

EMBEDDED_DEV_MAP_URL = 'https://developer.plugshare.com/embed'


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
    

class SearchCriterion():
    def __init__(
        self,
        latitude: float,
        longitude: float,
        radius_in_miles: float,
        wait_time_for_map_pan: float
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.radius = radius_in_miles
        self.time_to_pan = wait_time_for_map_pan


class MainMapScraper:

    def __init__(
        self,
        save_file_directory: str,
        save_every: int = 100,
        timeout: int = 3,
        page_load_pause: int = 1.5,
        headless: bool = True
    ):
        self.timeout = timeout
        self.save_path = save_file_directory
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
        try:
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
        
        except (NoSuchElementException, TimeoutException) as e_cookies:
            logger.error("Cookie banner or 'Manage Settings' link not found. "
                         "Assuming cookies are not rejected.")
    
    
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
        
    def save_checkpoint(self, data: Union[pd.DataFrame, Set[str]], data_name: str):
        logger.info(f"Saving checkpoint '{data_name}'...")
                
        path = self.save_path + f"{data_name}.pkl"
        if isinstance(data, pd.DataFrame):
            data.to_pickle(path)
        elif isinstance(data, set):
            joblib_dump(data, path)
            
        logger.info("Save complete!")
        
    #TODO: add in saving to disk at X pages (pickle for now)
    def run(
        self,
        locations: List[str] = None,
        start_location: int = None,
        end_location: int = None
    ):
        logger.info("Beginning scraping!")

        all_locations = []
        all_checkins = []
        
        if locations is not None:
            logger.info("`locations` is not None, so using that")        
        elif start_location is not None and end_location is not None:
            logger.info(f"Building location ID list covering "
                        f"[{start_location}, {end_location}], inclusive")
            locations = list(range(start_location, end_location+1))
        elif start_location is None or end_location is None and locations is None:
            raise ValueError("Either `locations` must not be None or both "
                             "`start_location` AND `end_location` must not be None")
        
        for i, location_id in enumerate(tqdm(
            locations,
            desc="Parsing stations"
        )):
            url = f"https://www.plugshare.com/location/{location_id}"
            self.driver.get(url)
            
            # Have to maximize to see all links...weirdly
            #TODO: if we can parse different locations without re-loading the window, move this to driver init
            self.driver.maximize_window()

            self.reject_all_cookies_dialog()
            self.exit_login_dialog()
            
            df_location, df_checkins = self.scrape_location(location_id)
            all_locations.append(df_location)
            all_checkins.append(df_checkins)
            
            if i+1 % self.save_every == 0:
                self.save_checkpoint(
                    pd.concat(all_locations, ignore_index=True),
                    data_name=f'df_locations_{i}'
                )
                self.save_checkpoint(
                    pd.concat(all_checkins, ignore_index=True),
                    data_name=f'df_checkins_{i}'
                )

            #TODO: tune between page switches
            logger.info(f"Sleeping for {self.page_load_pause} seconds")
            logger.warning("NEED TO TUNE THIS SLEEP TIME")
            sleep(self.page_load_pause)

        self.driver.quit()
        
        #TODO: add station location integers as column
        df_all_locations = pd.concat(all_locations, ignore_index=True)
        self.save_checkpoint(df_all_locations, data_name='df_all_locations')
        
        df_all_checkins = pd.concat(all_checkins, ignore_index=True)
        self.save_checkpoint(df_all_checkins, data_name='df_all_checkins')
        
        logger.info("Scraping complete!")
        return df_all_locations, df_all_checkins
    
#TODO: return results as DataFrame + de-duplicate by location ID    
class LocationIDScraper(MainMapScraper):
    
    def pick_plug_filters(
        self,
        plugs_to_use: List[str] = ALLOWABLE_PLUG_TYPES
    ):
        # Filter for only plug types we care about
        # First turn off all filters
        check_none_plug_type_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="outlet_off"]'))
        )
        check_none_plug_type_button.click()

        # Get all plug type filter items
        plug_type_elements = self.driver\
            .find_element(By.XPATH, '//*[@id="outlets"]')\
                .find_elements(By.XPATH, './child::*')

        # Filter for the plug types we care about
        plug_types_of_interest = [
            p for p in plug_type_elements if p.text in plugs_to_use
        ]

        # Click the ones we care about
        for p in plug_types_of_interest:
            checkbox = p.find_element(
                By.CSS_SELECTOR,
                'input[type="checkbox"]'
            )
            checkbox.click()
            
    def search_location(
        self,
        search_criterion: SearchCriterion
        ):
        
        # Just in case we're not seeing default content initially
        self.driver.switch_to.default_content()
        
        # Clear lat/long search box and then put in our new lat/long combo
        coordinate_search_box = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="search"]'))
        )
        coordinate_search_box.clear()
        coordinate_search_box.send_keys(",".join([
            str(search_criterion.latitude),
            str(search_criterion.longitude)
        ]))

        # Clear search radius (miles) box and add our radius in
        radius_search_box = self.driver.find_element(By.XPATH, '//*[@id="radius"]')
        radius_search_box.clear()
        radius_search_box.send_keys(search_criterion.radius)

        # Search!
        search_button = self.driver.find_element(By.XPATH, '//*[@id="geocode"]')
        search_button.click()
        
        # Give the iframe a moment to pan
        sleep(search_criterion.time_to_pan)
        
    
    def scroll_back_to_map_view(self, map_iframe: WebElement):
        '''
        Scrolls to iframe so pins are fully in viewport for clicking/scraping

        Parameters
        ----------
        map_iframe_element : WebElement
            WebElement for the iframe
        '''
        # Scroll to iframe so pins are in viewport and we can click/scrape them
        # 1) Get the iframe height
        iframe_height = int(map_iframe.get_attribute("height"))

        # 2) Scroll up to the element
        ActionChains(self.driver)\
                .scroll_to_element(map_iframe)\
                .perform()
                
        # Get current window position and scroll up to current_y + iframe_height/2
        current_window_coords = self.driver.execute_script(
            "return [window.pageXOffset, window.pageYOffset]"
        )

        # Note that y-coord is measured 0 at top of page -> more positive as it scrolls down
        self.driver.execute_script(
            f"window.scrollTo({current_window_coords[0]}, {current_window_coords[1] - int(iframe_height)})"
        )
        
    def parse_location_link(self, pin_element) -> str:
        pin_element.click()
        location_link = self.wait.until(EC.visibility_of_element_located((
            By.XPATH,
            '//*[@id="charger_info_footer"]/a'
        )))
        link_parsed = urlparse(location_link.get_attribute('href'))
        return link_parsed.path.rsplit("/", 1)[-1]
    
    def find_and_use_map_iframe(self) -> WebElement:
        map_iframe = self.driver.find_element(
            By.XPATH,
            '//*[@id="widget"]/iframe'
        )
        self.scroll_back_to_map_view(map_iframe)
        self.driver.switch_to.frame(map_iframe)
        
        return map_iframe
    
    def grab_location_ids(
        self,
        search_criterion: SearchCriterion
        ) -> List[str]:
        
        # Find the map iframe and move so it's in full view for scraping
        map_iframe = self.find_and_use_map_iframe()

        # Grab map pins seen for chargers in map viewport
        try:
            pins = self.wait.until(EC.visibility_of_all_elements_located((
                By.CSS_SELECTOR,
                'img[src="https://maps.gstatic.com/mapfiles/transparent.png"]'
            )))
            
        except TimeoutException:
            logger.error("No pins found here, moving on!")
            return None

        num_pins_in_view = len(pins)
        
        # Pull location ID from pin 
        # and then search again to pull map frame back to see all pins
        # Have to do this each time due to map panning when pin click happens
        # And have to re-find pins so WebElement for each pin doesn't go stale
        location_ids = []
        for i in range(num_pins_in_view):
        # Do another search if it's not the first time
            if i != 0:
                self.search_location(search_criterion)
                map_iframe = self.find_and_use_map_iframe()

                pins = self.wait.until(EC.visibility_of_all_elements_located((
                    By.CSS_SELECTOR,
                    'img[src="https://maps.gstatic.com/mapfiles/transparent.png"]'
                )))

            try:
                location_ids.append(self.parse_location_link(pins[i]))
            except (ElementClickInterceptedException, ElementNotInteractableException):
                logger.error("Pin %s not clickable", i)
            except (NoSuchElementException):
                logger.error("Pin %s not found weirdly...", i)
                
        return location_ids
    
    def run(
        self,
        search_criteria: List[SearchCriterion],
        plugs_to_include: List[str] = ALLOWABLE_PLUG_TYPES,
        ) -> pd.DataFrame:
        logger.info("Beginning location ID scraping!")
        
        # Load up the page
        self.driver.maximize_window()
        self.driver.get(EMBEDDED_DEV_MAP_URL)
        
        # Select only the plug filters we care about
        self.pick_plug_filters(plugs_to_include)
        
        dfs = []
        for i, search_criterion in enumerate(tqdm(
            search_criteria,
            desc="Searching map tiles"
        )):
            self.search_location(search_criterion)
            location_ids = self.grab_location_ids(search_criterion)
            if location_ids is None:
                continue
            
            num_locations_found = len(location_ids)
            dfs.append(pd.DataFrame({
                'parsed_datetime': [get_current_datetime()] * num_locations_found,
                'plug_types_searched': [plugs_to_include] * num_locations_found,
                'location_id': location_ids,
                'search_cell_latitude': [search_criterion.latitude] * num_locations_found,
                'search_cell_longitude': [search_criterion.longitude] * num_locations_found,
            }))
            
            # Save checkpoint
            if i+1 % self.save_every == 0 and len(dfs) > 0:
                self.save_checkpoint(
                    pd.concat(dfs, ignore_index=True),
                    data_name=f'df_location_ids_{i}'
                )
            
            sleep(search_criterion.time_to_pan)

        # self.driver.switch_to.default_content()
        self.driver.quit()

        if not df_locations.empty:
            df_locations = pd.concat(dfs, ignore_index=True)\
                .drop_duplicates(subset=['location_id'])
            self.save_checkpoint(df_locations, "df_location_ids")
            logger.info("All location IDs scraped (that we could)!")
            return df_locations
        
        else:
            logger.error("Something went horribly wrong, why do we have ZERO locations?!")
            return None