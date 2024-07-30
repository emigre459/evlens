from typing import List, Dict, Union, Sequence, Tuple
import os

import pandas as pd
import numpy as np

import openrouteservice as ors

from evlens.logs import setup_logger
logger = setup_logger(__name__)


def get_openrouting_route(
    start_coordinates: Tuple[float, float], # long, lat
    end_coordinates: Tuple[float, float],
    reverse_coordinates: bool = False,
    ors_api_key: str = None
) -> List[List[float]]:
    
    if ors_api_key is None:
        ors_api_key = os.getenv('ORS_API_KEY')
        
    if reverse_coordinates:
        start_coordinates = tuple(reversed(start_coordinates))
        end_coordinates = tuple(reversed(end_coordinates))
        
    client = ors.Client(key=ors_api_key)
    route = client.directions(
        coordinates=[start_coordinates, end_coordinates],
        profile='driving-car',
        format='geojson'
    )
    
    # Extract only the coordinates and make them lat-long
    lat_long_coords = [list(reversed(coord)) for coord in route['features'][0]['geometry']['coordinates']]
    
    return lat_long_coords