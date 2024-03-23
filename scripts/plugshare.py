import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

class Scraper:

    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-notifications")
        self.prefs = {"profile.default_content_setting_values.geolocation" :2} #TURN OFF LOCATION!!! (NOT NECESSARY BUT LESS TIME NEEDED)
        self.chrome_options.add_experimental_option("prefs", self.prefs)
        self.chrome_options.add_experimental_option("detach", True)

    
    def scrape_plugshare_locations(self, start_location, end_location):
        
        driver = webdriver.Chrome(options=self.chrome_options) # Open connection!
        all_stations = []

        for location_id in reversed(range(start_location, end_location)):
            try:
                url = f"https://www.plugshare.com/location/{location_id}" #DESIRED URL
                driver.get(url)
                time.sleep(1)  # Allow time for the page to load!!

                esc_button = driver.find_element(By.XPATH, "//*[@id=\"dialogContent_authenticate\"]/button/md-icon")
                esc_button.click()
        
                name = driver.find_element(By.XPATH, "//*[@id=\"display-name\"]/div/h1").text
                address = driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
                rating = driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
                hours = driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
                wattage = driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
                all_stations.append({"Name": name, "Address": address, "Rating": rating, "Wattage": wattage, "Hours": hours})

            except:
                continue

            time.sleep(1)


        driver.quit()
        df = pd.DataFrame(all_stations)
        return df 
    
#RUN THE FUNCTION!

s = Scraper()


start = time.time()

caller = s.scrape_plugshare_locations(100000,100015)
print(caller)

end = time.time()

print('\n', end - start, "seconds")