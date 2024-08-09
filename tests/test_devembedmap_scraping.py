from time import time
from roadtrip.data.plugshare import LocationIDScraper, SearchCriterion
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from roadtrip.data.google_cloud import BigQuery

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

from roadtrip.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")

# Moynihan Train Station - should have only one pin for CCS
TEST_COORDS = (40.7525834,-73.9999498) # Lat, long
RADIUS = 1 # miles
SLEEP_FOR_IFRAME_PAN = 1.5

bq = BigQuery()
id_of_interest = '0b8a3cc1-bcb6-440a-8dbd-4b84d1d795d5'
cell_data = bq.query_to_dataframe(f"SELECT * from evlens.plugshare.searchTiles WHERE id = '{id_of_interest}'").loc[0]

sc = SearchCriterion(
    latitude=cell_data['latitude'],
    longitude=cell_data['longitude'],
    radius_in_miles=cell_data['cell_radius_mi'],
    search_cell_id=cell_data['id'],
    search_cell_id_type='Manual',
    wait_time_for_map_pan=3
)


if __name__ == '__main__':
    start_time = time()
    lis = LocationIDScraper(
        f"./data/external/plugshare/{TODAY_STRING}/",
        timeout=3,
        headless=True,
        progress_bars=True
    )
    df_location_ids = lis.run([sc])

    print(f"Took {time() - start_time} seconds to execute")
    assert not df_location_ids.empty, "Scrape results empty"
    print(df_location_ids)