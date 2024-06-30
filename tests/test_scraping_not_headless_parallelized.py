from evlens.data.plugshare import ParallelMainMapScraper
from evlens.concurrency import parallelized_data_processing

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


if __name__ == '__main__':
    LOCATION_COUNT = 12
    locations = [TEST_LOCATION] * LOCATION_COUNT
    N_JOBS = 11
    
    #TODO: tune how long we need to sleep and timeout
    results = parallelized_data_processing(
        ParallelMainMapScraper,
        locations,
        n_jobs=N_JOBS,
        save_filepath = f"data/external/plugshare/{TODAY_STRING}/",
        error_screenshot_savepath = f"data/external/plugshare/{TODAY_STRING}/errors/",
        timeout=5,
        headless=False,
        progress_bars=False
    )
    
    
    assert len(results) == N_JOBS, f"Found {len(results)} batches, not the {N_JOBS} expected"
    num_locations_scraped = sum([len(e) for e in results])
    assert num_locations_scraped == LOCATION_COUNT, f"Found {num_locations_scraped} locations, not the {LOCATION_COUNT} expected"
    
    #TODO: add more tests to check that all data is there