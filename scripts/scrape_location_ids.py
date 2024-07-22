from typing import Literal, Union
import os
from time import time
from evlens.data.plugshare import ParallelLocationIDScraper, SearchCriterion
from evlens.data.google_cloud import BigQuery
from evlens.concurrency import parallelized_data_processing

from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd
from tqdm import tqdm
import pandas as pd

from evlens.logs import setup_logger
logger = setup_logger(__name__, send_to_gcp=True)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


def make_criteria(
    search_tile: pd.Series,
    tile_type: Union[Literal['Manual'], Literal['NREL']],
    map_pan_time: float = 3
) -> SearchCriterion:
    '''
    Using a geographically-bounded search tile, generates a SearchCriterion object representing it.

    Parameters
    ----------
    search_tile : pd.Series
        A pandas Series representing data for a single search cell. Expected to have, at a minimum, index labels of ['latitude', 'longitude', 'cell_radius_mi', 'id']
    tile_type : Union[Literal[&#39;Manual&#39;], Literal[&#39;NREL&#39;]]
        Indicates which type of search tile (brute force manual or NREL-derived) we are using
    map_pan_time : float, optional
        Timeout (in seconds) used for waiting for the map to do something, be that pan to a new location or load its pins up fully, by default 3

    Returns
    -------
    SearchCriterion
        SearchCriterion object that can be fed to our location scraper
    '''
    return SearchCriterion(
        latitude=search_tile.latitude,
        longitude=search_tile.longitude,
        radius_in_miles=search_tile.cell_radius_mi,
        search_cell_id=search_tile.id,
        search_cell_id_type=tile_type,
        wait_time_for_map_pan=map_pan_time
    )


#TODO: tune how long we need to sleep and timeout
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "map_tile_query",
        type=str,
        help="SQL query to pull down search tiles for systematically scraping location IDs by geographic space/tile. Will be applied to Google BigQuery to get tile data such as lat/long."
    )
    parser.add_argument(
        "--search_tile_type",
        type=str,
        default='NREL',
        help="Whether our brute force ('Manual') search tiles were used or our more focused (but less comprehensive) NREL-derived ones were."
    )
    parser.add_argument(
        "--starting_criterion_index",
        type=int,
        default=0,
        help="The starting index for the criterion (default: 0). Useful for restarting from a checkpoint in case the code breaks before completing"
    )
    args = parser.parse_args()
    
    # Get the search tiles from BigQuery
    bq = BigQuery()
    search_tiles = bq.query_to_dataframe(args.map_tile_query)
    
    tqdm.pandas(desc="Creating SearchCriterion objects")
    tiles = search_tiles.progress_apply(
        make_criteria,
        axis=1,
        tile_type=args.search_tile_type,
        map_pan_time=3
    )
    
    # Setup save directory so we don't have a race condition setting it up
    error_path = f"data/external/plugshare/{TODAY_STRING}/errors/"
    if not os.path.exists(error_path):
        logger.warning("Error screenshot save filepath does not exist, creating it...")
        os.makedirs(error_path)
    
    #TODO: make checkpoint resumption better (currently doesn't work for all but the first worker...)
    results = parallelized_data_processing(
        ParallelLocationIDScraper,
        tiles[args.starting_criterion_index:],
        n_jobs=-1,
        error_screenshot_savepath=error_path,
        timeout=3,
        headless=True,
        progress_bars=False,
        save_every=100
    )
    print("Scraping done!")