import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Scraper:

    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-notifications")
        self.prefs = {"profile.default_content_setting_values.geolocation" :2} #TURN OFF LOCATION!!! (NOT NECESSARY BUT LESS TIME NEEDED)
        self.chrome_options.add_experimental_option("prefs", self.prefs)
        #chrome_options.add_experimental_option("detach", True)

    
    def scrape_plugshare_locations(self, start_location, end_location):
        
        driver = webdriver.Chrome(options=self.chrome_options) # Open connection!
        all_stations = []

        for location_id in range(start_location, end_location):
            try:
                url = f"https://www.plugshare.com/location/{location_id}" #DESIRED URL
                driver.get(url)
            except:
                continue

            time.sleep(3)  # Allow time for the page to load!!

            try:
                login = driver.find_element(By.XPATH, "//*[@id=\"dialogContent_authenticate\"]/div[2]/div[2]/span")
                login.click()
                
                email = driver.find_element(By.XPATH, "//*[@id=\"email\"]")
                email.send_keys("kingdan017@gmail.com")
                
                password = driver.find_element(By.XPATH, "//*[@id=\"input_259\"]")
                password.send_keys("PlugShareTemp1")
                
                final_login = driver.find_element(By.XPATH, "//*[@id=\"auth-form\"]/md-content/div[5]/button")
                final_login.click()
                
                #esc_button = driver.find_element(By.XPATH, "//*[@id=\"dialogContent_authenticate\"]/button/md-icon")
                #esc_button.click()
            except:
                pass

            try: ## FIND STATION NAME
                name = driver.find_element(By.XPATH, "//*[@id=\"display-name\"]/div/h1").text
            except:
                name = "NA"
            
            try: ## FIND STATION ADDRESS
                address = driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
            except:
                address = "NA"
            
            try: ## FIND STATION RATING
                rating = driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
            except:
                rating = "NA"

            try: ## FIND STATION WATTAGE
                wattage = driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
            except:
                wattage = "NA"
            
            try: ## FIND STATION HOURS
                hours = driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
            except:
                hours = "NA"

            try:
                checkins = driver.find_element(By.XPATH, "//*[@id=\"checkins\"]").text
                checkins = checkins.split(' ')[1].split('\n')[0]
                #checkins = checkins.split('\n')[0]
                comments = driver.find_elements(By.CLASS_NAME, "user")
                cars = driver.find_elements(By.CLASS_NAME, "car ng-binding")

                for comment in comments:
                    #print(comment.text)
                    print(comment.text.replace("check_circle",""))

                for car in cars:
                    print(car)
                    
            except:
                checkins = "NA"

            try:
                nearby_locations = driver.find_elements(By.CLASS_NAME, "location ng-scope mapreact")
                for location in nearby_locations:
                    print(location.text)

            except:
                nearby_locations = "NA"
            
            try:
                score = driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
            except:
                score = "NA"

            if (name and address and rating and wattage and hours) == "NA":
                continue
            
            try:
                all_stations.append({"Name": name, "Address": address, "Rating": rating, "Wattage": wattage, "Hours": hours, "Checkins": checkins, score: "Score"})
            except:
                pass

            time.sleep(1)


        driver.quit()
        df = pd.DataFrame(all_stations)
        return df 
    
#RUN THE FUNCTION!
s = Scraper()


start = time.time()

caller = s.scrape_plugshare_locations(100000,100015)
caller.to_csv('Plugshare.csv', index = False)
print(caller)

end = time.time()

print('\n', end - start, "seconds")