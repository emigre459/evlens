from time import time
from evlens.data.plugshare import LocationIDScraper, SearchCriterion
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd
from tqdm import tqdm

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")
DEFAULT_SAVE_PATH = f"./data/external/plugshare/{TODAY_STRING}/"

SELENIUM_WAIT_TIME = 3
SLEEP_FOR_IFRAME_PAN = 1.5 # this has been tested but not in headless mode, maybe can go faster?

TEST_COORDS = (40.7525834,-73.9999498) # Lat, long
RADIUS = 1 # miles


#TODO: tune how long we need to sleep and timeout
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "map_tile_filepath",
        type=str,
        help="The filepath to the map tile coordinates pickle file (dataframe). If run from repo root, commonly the value is 'references/h3_hexagon_coordinates.pkl'"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_SAVE_PATH,
        help="The directory to save the scraped data in"
    )
    parser.add_argument(
        "--starting_criterion_index",
        type=int,
        default=0,
        help="The starting index for the criterion (default: 0). Useful for restarting from a checkpoint file (e.g. start at i+1 if file is marked as `_{i}.pkl`)"
    )
    args = parser.parse_args()
    
    lis = LocationIDScraper(
        args.output_dir,
        timeout=SELENIUM_WAIT_TIME,
        headless=True
    )
    
    # Grab our map of USA with hexagonal tiles for searching
    # Should have columns [latitude, longitude, cell_area_sq_miles]
    df_map_tiles = pd.read_pickle(args.map_tile_filepath)
    
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
    df_location_ids = lis.run(
        criteria[args.starting_criterion_index:],
        progress_bar_start=args.starting_criterion_index
    )