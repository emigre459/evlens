import time
from evlens.data.plugshare import Scraper

from evlens.logs import setup_logger
logger = setup_logger(__name__)

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

   
if __name__ == '__main__':
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
