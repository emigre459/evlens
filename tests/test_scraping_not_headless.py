from evlens.data.plugshare import Scraper
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

from evlens.logs import setup_logger
logger = setup_logger(__name__)
logger.info("TEST!")

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


if __name__ == '__main__':
    s = Scraper(
        f"../data/external/plugshare/{TODAY_STRING}/",
        timeout=3,
        headless=False
    )
    df_locations, df_checkins = s.run(TEST_LOCATION, TEST_LOCATION)
    
    assert not df_locations.empty, "Location metadata empty"
    assert not df_checkins.empty, "No checkins found"