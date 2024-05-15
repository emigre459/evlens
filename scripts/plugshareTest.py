import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#currentCount = 0
#currentCounter2 = 1

class Scraper:

    def __init__(self):
        self.currentCount = 0
        self.currentCounter2 = 1
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-infobars")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-notifications")
        self.prefs = {"profile.default_content_setting_values.geolocation":2} #TURN OFF LOCATION!!! (NOT NECESSARY BUT LESS TIME NEEDED)
        self.chrome_options.add_experimental_option("prefs", self.prefs)
        #chrome_options.add_experimental_option("detach", True)

    def plugshare_login(self):
        try:
            login = self.driver.find_element(By.XPATH, "//*[@id=\"dialogContent_authenticate\"]/div[2]/div[2]/span")
            login.click()
                
            email = self.driver.find_element(By.XPATH, "//*[@id=\"email\"]")
            email.send_keys("kingdan017@gmail.com")
                
            password = self.driver.find_element(By.XPATH, "//*[@id=\"input_259\"]")
            password.send_keys("PlugShareTemp1")
                
            final_login = self.driver.find_element(By.XPATH, "//*[@id=\"auth-form\"]/md-content/div[5]/button")
            final_login.click()
                
            time.sleep(2)
                #esc_button = driver.find_element(By.XPATH, "//*[@id=\"dialogContent_authenticate\"]/button/md-icon")
                #esc_button.click()
        except:
            pass
    
    def data_scrape(self):
        try: ## FIND STATION NAME
            self.name = self.driver.find_element(By.XPATH, "//*[@id=\"display-name\"]/div/h1").text
        except:
            self.name = "NA"
        
        try: ## FIND STATION ADDRESS
            self.address = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[3]/div[2]/a[1]").text
        except:
            self.address = "NA"
        
        try: ## FIND STATION RATING
            self.rating = self.driver.find_element(By.XPATH, "//*[@id=\"plugscore\"]").text
        except:
            self.rating = "NA"

        try: ## FIND STATION WATTAGE
            self.wattage = self.driver.find_element(By.XPATH, "//*[@id=\"ports\"]/div[3]").text
        except:
            self.wattage = "NA"
            
        try: ## FIND STATION HOURS
            self.hours = self.driver.find_element(By.XPATH, "//*[@id=\"info\"]/div[2]/div[11]/div[2]/div").text
        except:
            self.hours = "NA"

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
        self.all_stations = []

        for location_id in range(start_location, end_location):
            self.locationlist.append(location_id)

            try:
                url = f"https://www.plugshare.com/location/{location_id}" #DESIRED URL
                self.driver.get(url)
            except:
                continue

            
            time.sleep(3)  # Allow time for the page to load!!

            self.plugshare_login()

            self.data_scrape()

            time.sleep(1)



        self.driver.quit()
        df = pd.DataFrame(self.all_stations)
        return df 
    
#RUN THE FUNCTION!
s = Scraper()


start = time.time()

caller = s.scrape_plugshare_locations(100000,200000)
#caller.to_pickle("plugshare.pkl")
caller.to_csv('PlugshareScrape.csv', index = False)
caller.to_parquet('PlugshareScrape.parquet')
caller.to_parquet(f'Plugshare{s.currentCount}.parquet')
caller.to_csv(f'Plugshare{s.currentCount}.csv', index = False)
print(caller)

end = time.time()

print('\n', end - start, "seconds")
