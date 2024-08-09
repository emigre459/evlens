from roadtrip.data.plugshare import ParallelMainMapScraper
from roadtrip.concurrency import parallelized_data_processing
from roadtrip.data.google_cloud import BigQuery

import os

from roadtrip.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")

LOCATION_COUNT = 5

if __name__ == '__main__':
    bq = BigQuery()
    query =  query = f"""
    SELECT location_id
    FROM `{bq._make_table_id('plugshare', 'locationID')}`
    LIMIT {LOCATION_COUNT}
    """
    location_ids = bq.query_to_dataframe(query)['location_id']
    
    N_JOBS = 4
    
    # Setup save directory so we don't have a race condition setting it up
    error_path = f"data/external/plugshare/{TODAY_STRING}/errors/"
    if not os.path.exists(error_path):
        logger.warning("Error screenshot save filepath does not exist, creating it...")
        os.makedirs(error_path)
    
    #TODO: tune how long we need to sleep and timeout
    results = parallelized_data_processing(
        ParallelMainMapScraper,
        location_ids,
        n_jobs=N_JOBS,
        error_screenshot_savepath=error_path,
        timeout=3,
        page_load_pause=1,
        headless=True,
        progress_bars=False,
        save_every=100
    )
    
    assert len(results) == N_JOBS, f"Found {len(results)} batches, not the {N_JOBS} expected"
    
    # Each element is (df_stations, df_checkins, df_evses)
    num_locations_scraped = sum([len(e[0]) for e in results])
    assert num_locations_scraped == LOCATION_COUNT, f"Found {num_locations_scraped} locations, not the {LOCATION_COUNT} expected"
    
    #TODO: add more tests to check that all data is there
    print("SUCCESS!")