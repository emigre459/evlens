from time import time
from evlens.data.plugshare import LocationIDScraper, SearchCriterion
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd
from tqdm import tqdm

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")

SELENIUM_WAIT_TIME = 3
SLEEP_FOR_IFRAME_PAN = 1.5 # this has been tested but not in headless mode, maybe can go faster?

TEST_COORDS = (40.7525834,-73.9999498) # Lat, long
RADIUS = 1 # miles


#TODO: tune how long we need to sleep and timeout
#TODO: add argparsing for indicating what criterion we should start with (e.g. for resuming from a checkpoint)
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--starting_criterion_index",
        type=int,
        default=0,
        help="The starting index for the criterion (default: 0). Useful for restarting from a checkpoint file (e.g. start at i+1 if file is marked as `_{i}.pkl`)"
    )
    args = parser.parse_args()
    
    lis = LocationIDScraper(
        f"./data/external/plugshare/{TODAY_STRING}/",
        timeout=SELENIUM_WAIT_TIME,
        headless=True
    )
    
    # Grab our map of USA with hexagonal tiles for searching
    # Should have columns [latitude, longitude, cell_area_sq_miles]
    df_map_tiles = pd.read_pickle('references/h3_hexagon_coordinates.pkl')
    
    #TODO: build in functionality for starting from a checkpoint file i+1
    criteria = []
    
    for _, row in tqdm(
        df_map_tiles.iterrows(),
        desc='Building search criteria from gridded map',
        total=len(df_map_tiles)
    ):
        criteria.append(SearchCriterion(
            row['latitude'],
            row['longitude'],
            row['cell_radius_miles'],
            wait_time_for_map_pan=SLEEP_FOR_IFRAME_PAN
        ))
    df_location_ids = lis.run(criteria[args.starting_criterion_index:])