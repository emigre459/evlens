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
) -> Tuple[dict, List[List[float]]]:
    '''
    Uses OpenStreetRouting to calculate car-driving route coordinates from A to B. 

    Parameters
    ----------
    start_coordinates : Tuple[float, float]
        Start point coordinates in the form (longitude, latitude) unless `reverse_coordinates` is True.
    latend_coordinates : Tuple[float, float]
        End point coordinates in the form (longitude, latitude) unless `reverse_coordinates` is True.
    reverse_coordinates : bool, optional
        Indicates if input coordinates are of form (latitude, longitude) and need to be reversed before being using by OSR, by default False
    ors_api_key : str, optional
        OSR API key, by default None. If None, will look for the ORS_API_KEY env var

    Returns
    -------
    Tuple[dict, List[List[float]]]
        Full route metadata and data and coordinate list in format [(latitude1, longitude1), (etc)], resp. Latter is useful for Folium usage, former is useful for generating Linestring to query things like NREL APIs.
    '''
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
    
    return route, lat_long_coords