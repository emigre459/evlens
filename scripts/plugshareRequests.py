import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

class Scraper:

  def __init__(self):
    self.headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }

  def scrape_plugshare_locations(self, start_location, end_location):
    all_stations = []

    for location_id in reversed(range(start_location, end_location)):
      url = f"https://www.plugshare.com/location/{location_id}"
      response = requests.get(url, headers=self.headers)

      if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        try:
          name = soup.find("h1", {"id": "display-name"}).text.strip()
          address = soup.find("a", {"class": "info-link"}).text.strip()
          rating = soup.find("span", {"id": "plugscore"}).text.strip()
          hours = soup.find("div", text="Hours").find_next_sibling("div").text.strip()
          wattage = soup.find("div", {"id": "ports"}).find_all("div")[2].text.strip()

          all_stations.append({
              "Name": name,
              "Address": address,
              "Rating": rating,
              "Wattage": wattage,
              "Hours": hours
          })
        except:
          continue

      time.sleep(1)

    df = pd.DataFrame(all_stations)
    return df


# RUN THE FUNCTION!

s = Scraper()

start = time.time()

caller = s.scrape_plugshare_locations(100000, 100015)
print(caller)

end = time.time()

print('\n', end - start, "seconds")
