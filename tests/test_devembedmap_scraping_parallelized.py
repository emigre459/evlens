from time import time
import os
from evlens.data.plugshare import ParallelLocationIDScraper, SearchCriterion
from evlens.concurrency import parallelized_data_processing
from evlens.data.google_cloud import BigQuery


from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


if __name__ == '__main__':
    TILE_COUNT = 12
    
    bq = BigQuery()
    query = f"""
    SELECT *
    FROM `{bq._make_table_id('plugshare', 'searchTilesNREL')}`
    LIMIT {TILE_COUNT}
    """
    search_tiles = bq.query_to_dataframe(query)
    
    def make_criteria(search_tile: SearchCriterion, tile_type: str, map_pan_time: float = 1.5):
        return SearchCriterion(
            latitude=search_tile.latitude,
            longitude=search_tile.longitude,
            radius_in_miles=search_tile.cell_radius_mi,
            search_cell_id=search_tile.id,
            search_cell_id_type=tile_type,
            wait_time_for_map_pan=map_pan_time
        )

    tiles = search_tiles.apply(make_criteria, axis=1, tile_type='NREL')
    
    start_time = time()
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