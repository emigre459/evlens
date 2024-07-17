from time import sleep
import pandas as pd
import numpy as np
import os
import re
from typing import Tuple, Set, Union, List
from urllib.parse import urlparse

from json import loads

# from selenium import webdriver
from seleniumwire2.utils import decode
from seleniumwire2 import webdriver
from selenium.webdriver import ActionChains
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
from selenium.webdriver.chrome.service import Service

from tqdm import tqdm
import ray
from tenacity import retry, wait_random_exponential

from evlens import get_current_datetime
from evlens.data.google_cloud import upload_file, BigQuery

import logging
# Reduce noisy logging from selenium-wire-2
selenium_logger = logging.getLogger('seleniumwire')
selenium_logger.setLevel(logging.ERROR)

from evlens.logs import setup_logger
logger = setup_logger(__name__)


ALLOWABLE_PLUG_TYPES = [
    'Tesla Supercharger',
    'SAE Combo DC CCS',
    'CHAdeMO',
    # 'J-1772'
]

EMBEDDED_DEV_MAP_URL = 'https://developer.plugshare.com/embed'


class CheckIn:
    '''
    Tracks all the different components of a single check-in and can return as a single-row pandas DataFrame to be used elsewhere.
    '''
    def __init__(
        self,
        checkin_element: WebElement,
        error_screenshot_savepath: str = None,
        error_screenshot_save_bucket: str = 'plugshare_scraping'
    ):
        self.element = checkin_element
        self.error_screenshot_savepath = error_screenshot_savepath
        self.error_screenshot_save_bucket = error_screenshot_save_bucket
        
    def save_error_screenshot(self, filename: str):
        filename = get_current_datetime() \
            + '_' + str(os.getpid()) + '_' + filename
            
        if self.error_screenshot_savepath is None:
            raise ValueError("`error_screenshot_savepath` must not be None")
        path = os.path.join(self.error_screenshot_savepath, filename)
        self.element.driver.save_screenshot(path)
        if self.error_screenshot_save_bucket is not None:
            upload_file(
                self.error_screenshot_save_bucket,
                path,
                "errors/" + filename
            )
            os.remove(path)
        else:
            logger.error(
                "No savepath or GCP bucket provided for error screenshot."
                )
            
    @classmethod
    def _get_power_number(cls, text: str) -> int:
        '''
        Extracts the value from a power string. E.g. "110 Kilowatts" returns the integer 110.

        Parameters
        ----------
        text : str
            The text to extract the leading number from

        Returns
        -------
        int
            The value in the string
        '''
        if text is None or pd.isna(text):
            return np.nan
        elif isinstance(text, (int, float)):
            return text
        
        match = re.search(r"\d+", text)
        if match:
            return int(match.group(0))
        return np.nan
        
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
                    output['charge_power_kilowatts'] = self.__class__._get_power_number(d.text)
                elif d.get_attribute("class") == 'comment ng-binding':
                    output['comment'] = d.text
                    
        except NoSuchElementException:
            logger.debug("Checkin entry blank/not found")
            
        except Exception:
            logger.error(
                "Unknown error in parsing checkin entry, saving screenshot",
                exc_info=True
            )
            self.save_error_screenshot("checkin_parsing_error.png")
        
        # Check what columns we're missing and fill with null
        expected_columns = [
            'id',
            'date',
            'car',
            'problem',
            'connector_type',
            'charge_power_kilowatts',
            'comment',
            'station_id'
        ]
        for c in expected_columns:
            if c not in output.keys():
                output[c] = np.nan
                
        df_out = pd.DataFrame(output, index=[0]).dropna(how='all')
        df_out['id'] = BigQuery.make_uuid()
        
        # Drop anything that is all-nulls when ignoring location_id
        return df_out
    

class SearchCriterion():
    def __init__(
        self,
        latitude: float,
        longitude: float,
        radius_in_miles: float,
        search_cell_id: str,
        search_cell_id_type: str,
        wait_time_for_map_pan: float
    ):
        self.cell_id = search_cell_id
        self.cell_type = search_cell_id_type # Can be "NREL" or "Manual"
        self.latitude = latitude
        self.longitude = longitude
        self.radius = radius_in_miles
        self.time_to_pan = wait_time_for_map_pan
        
    def __str__(self):
        out = f"Search cell of type '{self.cell_type}' at lat/long ({self.latitude}, {self.longitude}), with a search radius of {self.radius} miles."
        
        return out
        
    def __repr__(self):
        return str(self)

class MainMapScraper:

    def __init__(
        self,
        error_screenshot_savepath: str = None,
        error_screenshot_save_bucket: str = 'plugshare_scraping',
        save_every: int = 100,
        timeout: int = 3,
        page_load_pause: int = 1,
        headless: bool = True,
        progress_bars: bool = True
    ):
        self.timeout = timeout
        self.error_screenshot_savepath = error_screenshot_savepath
        self.error_screenshot_save_bucket = error_screenshot_save_bucket
        self.save_every = save_every
        self.page_load_pause = page_load_pause
        self.use_tqdm = progress_bars        
        self._bq_client = BigQuery(project='evlens')
        self._bq_dataset_name = 'plugshare'
        
        if self.error_screenshot_savepath is not None:    
            if not os.path.exists(self.error_screenshot_savepath):
                logger.warning("Error screenshot save filepath does not exist, creating it...")
                os.makedirs(self.error_screenshot_savepath)
                
        
        self.chrome_options = Options()
        
        # Required to avoid issues spinning up Chrome in docker/Linux
        self.chrome_options.add_argument('--no-sandbox')
        
        # Can't parse elements if the full window isn't visible, surprisingly
        self.chrome_options.add_argument('--start-maximized')
        
        # Removes automation infobar and other bot-looking things
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option("useAutomationExtension", False)
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Run without window open
        if headless:
            self.chrome_options.add_argument('--headless=new')
        
        # Get rid of kruft that will slow us down
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-notifications")
        
        # Turn off geolocation to speed things up
        self.prefs = {"profile.default_content_setting_values.geolocation":2} 
        self.chrome_options.add_experimental_option("prefs", self.prefs)
        
        self.driver = webdriver.Chrome(
            options=self.chrome_options,
            service=None
        )
        self.wait = WebDriverWait(self.driver, self.timeout)
        
        # Make sure we look less bot-like
        # Thanks to https://stackoverflow.com/a/53040904/8630238
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
        
    def save_error_screenshot(self, filename: str):
        filename = get_current_datetime() \
            + '_' + str(os.getpid()) + '_' + filename
            
        if self.error_screenshot_savepath is None:
            raise ValueError("`error_screenshot_savepath` must not be None")
        path = os.path.join(self.error_screenshot_savepath, filename)
        self.driver.save_screenshot(path)
        if self.error_screenshot_save_bucket is not None:
            upload_file(
                self.error_screenshot_save_bucket,
                path,
                "errors/" + filename
            )
            os.remove(path)
        else:
            logger.error(
                "No GCP bucket provided for error screenshot."
                )

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
                logger.error("Cookie banner or 'Manage Settings' link not found. Assuming cookies are not rejected.")
                self.driver.switch_to.default_content()
                
    def exit_login_dialog(self):
        logger.info("Attempting to exit login dialog...")
        try:
            # Wait for the exit button
            esc_button = self.wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//*[@id=\"dialogContent_authenticate\"]/button"
            )))
            esc_button.click()
            logger.info("Successfully exited the login dialog!")

        except (NoSuchElementException, TimeoutException):
            logger.error("Login dialog exit button not found.")
            self.save_error_screenshot("selenium_login_not_found.png")
            

        except Exception as e:
            logger.error(f"Unknown error trying to exit login dialog, saving error screenshot for later debugging", exc_info=True)
            self.save_error_screenshot("unknown_exit_dialog_error.png")
    
    #TODO: clean up and try to more elegantly extract things en masse
    def scrape_location(
        self,
        location_id: str
        ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        '''
        Scrapes a single location (single webpage)

        Returns
        -------
        Tuple[pd.DataFrame, pd.DataFrame]
            (Single-row dataframe with location metadata, dataframe with one row per check-in comment)
        '''
        if isinstance(location_id, int):
            logger.warning("location_id came through as int, should be str. Casting to str...")
            location_id = str(location_id).zfill(6)
        
        output = dict()
        
        logger.info("Starting page scrape...")
        try: ## FIND STATION NAME
            output['name'] = self.wait.until(EC.visibility_of_element_located((
                By.XPATH,
                "//*[@id=\"display-name\"]/div/h1"
            ))).text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station name error, skipping...")
            return (pd.DataFrame(), pd.DataFrame())
            
        try:
            output['station_owner'] = self.wait.until(EC.visibility_of_element_located((
                By.XPATH,
                '//*[@id="ports"]/div[2]/span'
            ))).text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Can't find station owner")
            output['station_owner'] = np.nan
            
        try:
            output['location_type'] = self.wait.until(EC.visibility_of_element_located((
                By.XPATH,
                '//*[@id="ports"]/div[4]'
            ))).text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Can't find location type")
            output['location_type'] = np.nan
        
        try: ## FIND STATION ADDRESS
            
            output['address'] = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station address error", exc_info=True)
            output['address'] = np.nan
        
        try: ## FIND STATION RATING
            
            output['plugscore'] = float(self.driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text)
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station rating error", exc_info=True)
            output['plugscore'] = np.nan

        try: ## FIND STATION WATTAGE
            
            output['wattage'] = self.driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Wattage error", exc_info=True)
            output['wattage'] = np.nan
            
        try: ## Parking details
            
            output['parking'] = self.driver.find_element(
                By.XPATH, 
                '//*[@id="info"]/div[2]/div[6]/div[2]'
                ).text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Parking data not found", exc_info=True)
            output['parking'] = np.nan
            
        try: ## FIND STATION HOURS
            
            output['service_hours'] = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Station hours error", exc_info=True)
            output['service_hours'] = np.nan
            
        try: ## Station details        
            output['description'] = self.driver.find_element(
                By.XPATH,
                '//*[@id="info"]/div[2]/div[12]/div[2]/span'
                ).text
            
        except (NoSuchElementException, TimeoutException):
            logger.error("No description found", exc_info=True)
            output['description'] = np.nan

        try: # Get total check-in counts
            def _get_checkin_count(text) -> Union[np.nan, int]:
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
            more_comments_link = self.wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//*[@id=\"checkins\"]/div[2]/span[3]"
            )))
            more_comments_link.click()
            
            detailed_checkins = self.driver.find_element(
                By.XPATH,
                "//*[@id=\"dialogContent_reviews\"]/div/div"
            ).find_elements(By.XPATH, "./child::*")
            
            self.detailed_checkins = detailed_checkins
            
            checkin_dfs = []
            if self.use_tqdm:
                iterator = tqdm(detailed_checkins, desc="Parsing checkins for location")
            else:
                iterator = detailed_checkins
            for checkin in iterator:
                c = CheckIn(checkin, self.error_screenshot_savepath)
                out = c.parse()
                if not out.empty:
                    checkin_dfs.append(out)
                
            if len(checkin_dfs) == 0:
                logger.error("No checkins found")
                df_checkins = pd.DataFrame()
            else:
                df_checkins = pd.concat(checkin_dfs, ignore_index=True)
                df_checkins['station_id'] = location_id
            
        except (NoSuchElementException, TimeoutException):
            logger.error("Comments error", exc_info=True)
            df_checkins = pd.DataFrame()
            
        except Exception:
            logger.error("Did we get blocked from clicking More Comments?", exc_info=True)
            self.save_error_screenshot('checkins.png')
            df_checkins = pd.DataFrame()
            
        logger.info("Page scrape complete!")
        df_station = pd.DataFrame(output, index=[0])
        df_station['location_id'] = location_id
        df_station['id'] = BigQuery.make_uuid()
        df_station['last_scraped'] = get_current_datetime(
            date_delimiter=None,
            time_delimiter=None
        )
        
        return (
            df_station,
            df_checkins
        )
        
    
    def save_to_bigquery(
        self,
        data: pd.DataFrame,
        table_name: str
    ):
        logger.info("Saving to BigQuery...")
        if data.empty:
            logger.error("`data` empty, not saving to BigQuery`")
        else:
            self._bq_client.insert_data(
                data,
                self._bq_dataset_name,
                table_name
            )
        
    def run(self, locations: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        logger.info("Beginning scraping!")

        all_stations = []
        all_checkins = []
        if self.use_tqdm:
            iterator = enumerate(tqdm(
                locations,
                desc="Parsing stations"
            ))
        else:
            iterator = enumerate(locations)
            
        #TODO: add some retry logic for rare "database can't connect" error
        for i, location_id in iterator:
            url = f"https://www.plugshare.com/location/{location_id}"
            self.driver.get(url)

            self.reject_all_cookies_dialog()                
            self.exit_login_dialog()
            df_station, df_checkins = self.scrape_location(location_id)
            
            if not df_station.empty:
                all_stations.append(df_station)
            if not df_checkins.empty:
                all_checkins.append(df_checkins)
            
            # Save to BQ
            if len(all_stations) >= self.save_every:
                logger.info(f"Saving checkpoint at index {i} and location {location_id}")
                
                df_stations_checkpoint = pd.concat(all_stations, ignore_index=True)
                df_checkins_checkpoint = pd.concat(all_checkins, ignore_index=True)
                self.save_to_bigquery(
                    df_stations_checkpoint,
                    'stations'
                )
                self.save_to_bigquery(
                    df_checkins_checkpoint,
                    'checkins'
                )
                
                all_stations = []
                all_checkins = []

            #TODO: tune between page switches
            logger.info(f"Sleeping for {self.page_load_pause} seconds")
            logger.warning("NEED TO TUNE THIS SLEEP TIME")
            sleep(self.page_load_pause)

        self.driver.quit()
        
        #TODO: add station location integers as column
        df_all_stations = pd.concat(all_stations, ignore_index=True)        
        df_all_checkins = pd.concat(all_checkins, ignore_index=True)
        self.save_to_bigquery(
            df_all_stations,
            'stations'
        )
        self.save_to_bigquery(
            df_all_checkins,
            'checkins'
        )
        
        logger.info("Scraping complete!")
        return df_all_stations, df_all_checkins
    
    
@ray.remote(max_restarts=3, max_task_retries=3)
class ParallelMainMapScraper(MainMapScraper):
    def save_to_bigquery(
        self,
        data: pd.DataFrame,
        table_name: str
    ):
        retry_strategy = retry(wait=wait_random_exponential(multiplier=0.5, min=0, max=10))
        retry_strategy(super().save_to_bigquery)(data, table_name)    
    
    
class LocationIDScraper(MainMapScraper):
    
    def _catch_api_response(self) -> pd.DataFrame:
        r = self.driver.wait_for_request(
            r'https://api.plugshare.com/v3/locations/region?',
            timeout=self.timeout
        )
        body = decode(r.response.body, r.response.headers.get("Content-Encoding", "identity"))

        df = pd.DataFrame(loads(body))
        del self.driver.requests
        
        return df
    
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
            EC.element_to_be_clickable((By.XPATH, '//*[@id="search"]'))
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
        search_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="geocode"]'))
        )
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
        pin = self.wait.until(EC.element_to_be_clickable(pin_element))
        pin.click()
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
        ) -> pd.DataFrame:
        
        # Find the map iframe and move so it's in full view for scraping
        map_iframe = self.find_and_use_map_iframe()

        # Grab map pins seen for chargers in map viewport
        # Can't do visibility check as some are hidden forever
        try:
            # Have to do a wait to make sure we can grab them at all
            sleep(search_criterion.time_to_pan)
            
            # Capture the API response that populates the map
            return self._catch_api_response()
            
        except (TimeoutException, NoSuchElementException):
            logger.error("No pins found here, moving on!", exc_info=True)
            return None
    
    def run(
        self,
        search_criteria: List[SearchCriterion],
        plugs_to_include: List[str] = ALLOWABLE_PLUG_TYPES,
        ) -> pd.DataFrame:
        logger.info("Beginning location ID scraping!")
        
        # Load up the page
        self.driver.get(EMBEDDED_DEV_MAP_URL)
        
        # Select only the plug filters we care about
        self.pick_plug_filters(plugs_to_include)
        
        dfs = []
        if self.use_tqdm:
            iterator = tqdm(
                search_criteria,
                desc="Searching map tiles"
            )
        else:
            iterator = search_criteria
        
        for i, search_criterion in enumerate(iterator):
            self.search_location(search_criterion)
            df_locations_found = self.grab_location_ids(search_criterion)
            if df_locations_found is None or df_locations_found.empty:
                continue
            
            if search_criterion.cell_type == 'NREL':
                cell_id_column = 'search_cell_id_nrel'
                unused_cell_id_column = 'search_cell_id'
            else:
                cell_id_column = 'search_cell_id'
                unused_cell_id_column = 'search_cell_id_nrel'
            
            num_locations_found = len(df_locations_found)
            print(f"{num_locations_found=:,}")
            try:
                dfs.append(pd.DataFrame({
                    'id': BigQuery.make_uuid(),
                    'parsed_datetime': [get_current_datetime(date_delimiter=None, time_delimiter=None)] * num_locations_found,
                    'plug_types': df_locations_found['connector_types'].str.join(';'),
                    'location_id': df_locations_found['id'].astype(str),
                    'latitude': df_locations_found['latitude'],
                    'longitude': df_locations_found['longitude'],
                    cell_id_column: [search_criterion.cell_id] * num_locations_found,
                    unused_cell_id_column: [None] * num_locations_found,
                    'under_repair': df_locations_found['under_repair']
                }))
            except KeyError as e:
                logger.error("Something went wrong with appending the data, running df.info() before raising error...")
                df_locations_found.info()
                raise e
                
            
            # Save checkpoint
            if len(dfs) > 0 and sum([len(df) for df in dfs]) >= self.save_every:
                logger.info("Saving checkpoint...")
                df_locations_checkpoint = pd.concat(dfs, ignore_index=True)\
                    .drop_duplicates(subset=['location_id'])
                self.save_to_bigquery(
                    df_locations_checkpoint,
                    'locationID'
                )
                # Try to save some memory
                # del dfs
                # del df_locations_checkpoint
                # gc.collect()
                dfs = []
            
            sleep(search_criterion.time_to_pan)

        # self.driver.switch_to.default_content()
        self.driver.quit()

        if len(dfs) > 0:
            df_locations_found = pd.concat(dfs, ignore_index=True)\
                .drop_duplicates(subset=['location_id'])
            self.save_to_bigquery(df_locations_found, "locationID")
            logger.info("All location IDs scraped (that we could)!")
            return df_locations_found
        
        else:
            logger.error("Something went horribly wrong, why do we have ZERO locations?!")
            return None



@ray.remote(max_restarts=3, max_task_retries=3)
class ParallelLocationIDScraper(LocationIDScraper):
    def save_to_bigquery(
        self,
        data: pd.DataFrame,
        table_name: str
    ):
        retry_strategy = retry(wait=wait_random_exponential(multiplier=0.5, min=0, max=10))
        retry_strategy(super().save_to_bigquery)(data, table_name)