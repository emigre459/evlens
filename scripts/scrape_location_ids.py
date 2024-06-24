from time import time
from evlens.data.plugshare import LocationIDScraper, SearchCriterion
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import pandas as pd
from tqdm import tqdm

from evlens.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")

SLEEP_FOR_IFRAME_PAN = 1.5


if __name__ == '__main__':
    lis = LocationIDScraper(
        f"./data/external/plugshare/{TODAY_STRING}/",
        timeout=3,
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
    df_location_ids = lis.run(criteria[:3])