from time import time
from evlens.data.plugshare import LocationIDScraper, SearchCriterion
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")

# Moynihan Train Station - should have only one pin for CCS
TEST_COORDS = (40.7525834,-73.9999498) # Lat, long
RADIUS = 1 # miles
SLEEP_FOR_IFRAME_PAN = 1.5


if __name__ == '__main__':
    start_time = time()
    lis = LocationIDScraper(
        f"./data/external/plugshare/{TODAY_STRING}/",
        timeout=3,
        headless=True,
        progress_bars=True
    )

    sc = SearchCriterion(
        TEST_COORDS[0],
        TEST_COORDS[1],
        RADIUS,
        1234, # fake,
        'Manual',
        SLEEP_FOR_IFRAME_PAN
    )
    df_location_ids = lis.run([sc])

    print(f"Took {time() - start_time} seconds to execute")
    
    assert not df_location_ids.empty, "Scrape results empty"
    
    # Should return [563873, 574882]
    print(df_location_ids)