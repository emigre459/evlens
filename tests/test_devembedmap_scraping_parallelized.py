from time import time
import os
from evlens.data.plugshare import ParallelLocationIDScraper, SearchCriterion
from evlens.concurrency import parallelized_data_processing

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")

# Moynihan Train Station - should have only one pin for CCS
TEST_COORDS = (40.7525834,-73.9999498) # Lat, long
RADIUS = 1 # miles
SLEEP_FOR_IFRAME_PAN = 1.5
TEST_CRITERION = SearchCriterion(
    TEST_COORDS[0],
    TEST_COORDS[1],
    RADIUS,
    '811d4a85-037a-4616-b944-2559c96ae459', # fake
    SLEEP_FOR_IFRAME_PAN
)


if __name__ == '__main__':
    start_time = time()
    TILE_COUNT = 12
    tiles = [TEST_CRITERION] * TILE_COUNT
    N_JOBS = 4
    
    # Setup save directory so we don't have a race condition setting it up
    error_path = f"data/external/plugshare/{TODAY_STRING}/errors/"
    if not os.path.exists(error_path):
        logger.warning("Error screenshot save filepath does not exist, creating it...")
        os.makedirs(error_path)
        
    results = parallelized_data_processing(
        ParallelLocationIDScraper,
        tiles,
        n_jobs=N_JOBS,
        error_screenshot_savepath=error_path,
        timeout=3,
        page_load_pause=0,
        headless=True,
        progress_bars=False
    )
    
    assert len(results) == N_JOBS, f"Found {len(results)} batches, not the {N_JOBS} expected"
    
    # Each element should have found two locations to scrape
    num_locations_scraped = sum([len(e) for e in results])
    assert num_locations_scraped == 2 * N_JOBS, f"Found {num_locations_scraped} locations, not the {2 * N_JOBS} expected"
    
    #TODO: add more tests to check that all data is there
    print("SUCCESS!")