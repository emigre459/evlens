from evlens.data.plugshare import ParallelScraper
from evlens.concurrency import parallelized_data_processing

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = 252784

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


if __name__ == '__main__':
    locations = [TEST_LOCATION, TEST_LOCATION, TEST_LOCATION]
    
    # Setup as many scrapers as we have locations (not usually how it would work, since we can only setup n_jobs scrapers and have more locations than that...)
    
    results = parallelized_data_processing(
        [ParallelScraper for _ in range(len(locations))],
        locations,
        save_filepath = f"../data/external/plugshare/{TODAY_STRING}/",
        timeout=3,
        headless=False
    )
    
    assert len(results) == 3, f"Found {len(results)} locations, not the 3 expected"