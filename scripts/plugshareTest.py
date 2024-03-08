import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import os
from dotenv import load_dotenv
load_dotenv(override=True)

class Scraper:

    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-notifications")
        self.prefs = {"profile.default_content_setting_values.geolocation" :2} #TURN OFF LOCATION!!! (NOT NECESSARY BUT LESS TIME NEEDED)
        self.chrome_options.add_experimental_option("prefs", self.prefs)
        #chrome_options.add_experimental_option("detach", True)
        
        self.driver = webdriver.Chrome(options=self.chrome_options) # Open connection!
        
    def login(self, username: str, password: str):
        
        try:
            self.driver.get("https://www.plugshare.com/")
        except:
            pass
        
        login = self.driver.find_element(By.XPATH, "//*[@id=\"dialogContent_authenticate\"]/div[2]/div[2]/span")
        login.click()
        
        email = self.driver.find_element(By.XPATH, "//*[@id=\"email\"]")
        email.send_keys(username)
        
        pass_xpath = self.driver.find_element(By.XPATH, "//*[@id=\"input_259\"]")
        pass_xpath.send_keys(password)
        
        final_login = self.driver.find_element(By.XPATH, "//*[@id=\"auth-form\"]/md-content/div[5]/button")
        final_login.click()
        
        #esc_button = driver.find_element(By.XPATH, "//*[@id=\"dialogContent_authenticate\"]/button/md-icon")
        #esc_button.click()

    
    def scrape_plugshare_locations(self, start_location, end_location):
        
        all_stations = []
        time.sleep(10)
        self.login(os.getenv('PLUGSHARE_EMAIL'), os.getenv("PLUGSHARE_PASSWORD"))

        for location_id in range(start_location, end_location):
            try:
                url = f"https://www.plugshare.com/location/{location_id}" #DESIRED URL
                self.driver.get(url)
            except:
                continue

            time.sleep(2)  # Allow time for the page to load!!

            try: ## FIND STATION NAME
                name = self.driver.find_element(By.XPATH, "//*[@id=\"display-name\"]/div/h1").text
            except:
                name = "NA"
            
            try: ## FIND STATION ADDRESS
                address = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
            except:
                address = "NA"
            
            try: ## FIND STATION RATING
                rating = self.driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
            except:
                rating = "NA"

            try: ## FIND STATION WATTAGE
                wattage = self.driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
            except:
                wattage = "NA"
            
            try: ## FIND STATION HOURS
                hours = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
            except:
                hours = "NA"

            try:
                checkins = self.driver.find_element(By.XPATH, "//*[@id=\"checkins\"]").text
                checkins = checkins.split(' ')[1].split('\n')[0]
                #checkins = checkins.split('\n')[0]
            except:
                checkins = "NA"

            if (name and address and rating and wattage and hours and checkins) == "NA":
                continue
            
            try:
                all_stations.append({"Name": name, "Address": address, "Rating": rating, "Wattage": wattage, "Hours": hours, "Checkins": checkins})
            except:
                pass

            time.sleep(1)


        self.driver.quit()
        df = pd.DataFrame(all_stations)
        return df 
    
#RUN THE FUNCTION!
s = Scraper()


start = time.time()

caller = s.scrape_plugshare_locations(313514,313524)
caller.to_csv('Plugshare.csv', index = False)
print(caller)

end = time.time()

print('\n', end - start, "seconds")