from evlens.data.plugshare import ParallelMainMapScraper
from evlens.concurrency import parallelized_data_processing

from joblib import dump
import os

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = '252784'

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


if __name__ == '__main__':
    LOCATION_COUNT = 12
    locations = [TEST_LOCATION] * LOCATION_COUNT
    N_JOBS = 4
    
    # Setup save directory so we don't have a race condition setting it up
    error_path = f"data/external/plugshare/{TODAY_STRING}/errors/"
    if not os.path.exists(error_path):
        logger.warning("Error screenshot save filepath does not exist, creating it...")
        os.makedirs(error_path)
    
    #TODO: tune how long we need to sleep and timeout
    results = parallelized_data_processing(
        ParallelMainMapScraper,
        locations,
        n_jobs=N_JOBS,
        error_screenshot_savepath=error_path,
        timeout=10,
        page_load_pause=0,
        headless=True,
        progress_bars=False
    )
    
    assert len(results) == N_JOBS, f"Found {len(results)} batches, not the {N_JOBS} expected"
    
    # Each element is (df_locations, df_checkins)
    num_locations_scraped = sum([len(e[0]) for e in results])
    assert num_locations_scraped == LOCATION_COUNT, f"Found {num_locations_scraped} locations, not the {LOCATION_COUNT} expected"
    
    #TODO: add more tests to check that all data is there
    print("SUCCESS!")