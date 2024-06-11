import time
from tqdm import tqdm
import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from evlens.logs import setup_logger
logger = setup_logger(__name__)

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

class Scraper:

    def __init__(self):
        self.currentCount = 0
        self.currentCounter2 = 1
        
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless=new')
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-notifications")
        self.chrome_options.add_argument("--disable-cookies")
        
        #TURN OFF LOCATION!!! (NOT NECESSARY BUT LESS TIME NEEDED)
        self.prefs = {"profile.default_content_setting_values.geolocation":2} 
        self.chrome_options.add_experimental_option("prefs", self.prefs)


        
    def exit_login_dialog(self):
        try:
            # Wait for the exit button
            wait = WebDriverWait(self.driver, 10)
            esc_button = wait.until(EC.visibility_of_element_located((
                By.XPATH,
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

    #TODO: deprecate this method?
    def reject_all_cookies_dialog(self):
        manage_settings_link = self.driver.find_element(
            By.LINK_TEXT,
            "Manage Settings"
        )
        manage_settings_link.click()
        
        reject_all_button = self.driver.find_element(
            By.XPATH,
            "//*[@id=\"denyAll\"]/span[1]/div/span"
        )
        reject_all_button.click()
        
        reject_all_confirm_button = self.driver.find_element(
            By.XPATH,
            "//*[@id=\"mat-dialog-0\"]/ng-component/app-theme/div/div/div[2]/button[2]"
        )
        reject_all_confirm_button.click()
    
    
    def data_scrape(self):
        try: ## FIND STATION NAME
            self.name = self.driver.find_element(By.XPATH, "//*[@id=\"display-name\"]/div/h1").text
        except:
            self.name = np.nan
        
        try: ## FIND STATION ADDRESS
            self.address = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
        except:
            self.address = np.nan
        
        try: ## FIND STATION RATING
            self.rating = self.driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
        except:
            self.rating = np.nan

        try: ## FIND STATION WATTAGE
            self.wattage = self.driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
        except:
            self.wattage = np.nan
            
        try: ## FIND STATION HOURS
            self.hours = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
        except:
            self.hours = np.nan

        try: # FIND CHECKINS 
            self.checkins = self.driver.find_element(By.XPATH, "//*[@id=\"checkins\"]").text
            self.checkins = self.checkins.split(' ')[1].split('\n')[0]
            #checkins = checkins.split('\n')[0]
        except:
            pass

        try: # FIND COMMENTS
           
            self.commentList = []
            self.comments = self.driver.find_elements(By.CLASS_NAME, "details")
            for comment in self.comments:
                self.commentList.append(comment.text)
                print(comment.text)
             
            for comment in self.commentList:
                comment.replace("check_circle", "")
            self.finalComments = ', '.join(self.commentList)
        except:
            pass

        try: # FIND NEARBY LOCATIONS
            #self.nearby_locations = self.driver.find_element(By.XPATH, "//*[@id=\"nearby\"]/div[2]/div[1]")
            #self.nearby_locations.click()
            time.sleep(3)
            #self.plugshare_login()
            #time.sleep(1)
            #self.data_scrape()
            #print(self.nearby_locations + "TOTAL NEARBY LOCATIONS LIST")
            #for location in self.nearby_locations:
                #print(location.text + "NEARBY LOCATIONS")

        except:
            pass
            
        try: # SCRAPE CAR
            carList = []
            self.cars = self.driver.find_elements(By.CLASS_NAME, "car ng-binding") # PRINTS TYPE OF CAR FOR EACH PERSON
            for car in self.cars:
                carList.append(car)
            self.cars = ', '.join(carList)
        except:
            pass
            
        try: # PUT ALL TOGETHER
            self.all_stations.append({"Name": self.name, "Address": self.address, "Rating": self.rating, "Wattage": self.wattage, "Hours": self.hours, "Checkins": self.checkins, "Comments": self.finalComments, "Car": self.cars})
        except:
            pass
        
    def scrape_plugshare_locations(self, start_location, end_location):
        if self.currentCounter2 % 100 == 0:
            self.currentCount += 1

        self.locationlist = []
        self.driver = webdriver.Chrome(options=self.chrome_options) # Open connection!
        time.sleep(15)
        # print(self.driver.get_cookies())
        # self.driver.add_cookie({'domain': ''})

        self.all_stations = []

        for location_id in tqdm(
            range(start_location, end_location+1),
            desc="Parsing stations"
        ):
            self.locationlist.append(location_id)

            url = f"https://www.plugshare.com/location/{location_id}" #DESIRED URL
            self.driver.get(url)

            
            time.sleep(3)  # Allow time for the page to load!!

            # self.plugshare_login()
            self.reject_all_cookies_dialog()
            self.exit_login_dialog()
            self.data_scrape()

            time.sleep(1)

        self.driver.quit()
        df = pd.DataFrame(self.all_stations)
        return df
    
if __name__ == '__main__':
    #RUN THE FUNCTION!
    s = Scraper()


    start = time.time()

    #TODO: can I remove one or more of these save calls? Seems duplicative.
    caller = s.scrape_plugshare_locations(TEST_LOCATION, TEST_LOCATION)
    #caller.to_pickle("plugshare.pkl")
    caller.to_csv('data/external/plugshare/PlugshareScrape.csv', index = False)
    caller.to_parquet('data/external/plugshare/PlugshareScrape.parquet')
    caller.to_parquet(f'data/external/plugshare/Plugshare{s.currentCount}.parquet')
    caller.to_csv(f'data/external/plugshare/Plugshare{s.currentCount}.csv', index = False)
    print(caller)

    end = time.time()

    print('\n', end - start, "seconds")
