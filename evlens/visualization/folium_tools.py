from typing import List, Dict, Union, Sequence, Tuple
import os

import pandas as pd
import numpy as np

from folium import Map, Marker, Icon, PolyLine

from evlens.logs import setup_logger
logger = setup_logger(__name__)

MOBILE_PIXEL_SIZE = (360, 640) # width, height

def get_single_point(
    coordinates: Sequence[float], # should be lat, long
    location_name: str,
    popup: bool = True,
    tooltip: bool = False,
    starting_zoom: int = 16,
    map_size: Tuple[int, int] = MOBILE_PIXEL_SIZE,
    include_zoom_widget: bool = True
) -> Map:
    map = Map(
        location=coordinates,
        zoom_start=starting_zoom,
        tiles='OpenStreetMap',
        width=map_size[0],
        height=map_size[1],
        zoom_control=include_zoom_widget
    )
    
    icon = Icon(color='blue', prefix='fa', icon='fa-solid fa-car')
    
    Marker(
        coordinates,
        draggable=True,
        popup=location_name if popup else None,
        tooltip=location_name if tooltip else None,
        icon=icon
    ).add_to(map)
    
    return map


def plot_route(
    start_coordinates: Sequence[float], # should be lat, long
    end_coordinates: Sequence[float],
    start_location_name: str,
    end_location_name: str,
    route_coordinates: Sequence[Sequence[float]] = None,
    starting_zoom: int = 7,
    map_size: Tuple[int, int] = MOBILE_PIXEL_SIZE,
    include_zoom_widget: bool = True
) -> Map:
    
    start_icon = Icon(color='green', icon='fa-solid fa-play', prefix='fa')
    end_icon = Icon(color='red', icon='fa-solid fa-stop', prefix='fa')
    
    map = Map(
        location=start_coordinates,
        zoom_start=starting_zoom,
        width=map_size[0],
        height=map_size[1],
        zoom_control=include_zoom_widget
    )
    Marker(
        start_coordinates,
        popup=start_location_name,
        icon=start_icon
        ).add_to(map)
    Marker(
        end_coordinates,
        popup=end_location_name,
        icon=end_icon
        ).add_to(map)
    
    if route_coordinates is not None:
        PolyLine(
            locations=route_coordinates,
            color='blue',
            weight=4,
            tooltip="Naive no-charging route",
            smooth_factor=2.0
        ).add_to(map)
    
    return map


def add_stations_to_map(
    data: pd.DataFrame,
    map: Map,
    networks_to_include: Union[str, List[str]] = 'all',
    tooltip: bool = False
) -> Map:
    
    df = data.copy()
    ev_networks_original = df['ev_network'].unique()
    if networks_to_include != 'all':
        if isinstance(networks_to_include, str):
            networks_to_include = [networks_to_include]
        df = df[df['ev_network'].isin(networks_to_include)]
        
    if df.empty:
        raise ValueError(f"No stations in allowed networks found, only found {ev_networks_original}")
    
    def build_station_text(row: pd.Series):
        address_string = row[['street_address', 'city', 'state']].fillna('').str.cat(sep=', ')
        if row['zip'] is not None:
            address_string += '  ' + row['zip']
            
        if row['station_name'] is None:
            station_name = 'No Name'
        else:
            station_name = row['station_name']
            
        station_name = f"<b>{station_name}</b>"
            
        if row['ev_network'] is None:
            network = 'Network Unknown'
        else:
            network = row['ev_network']

        text = station_name + "\n" + address_string + "\n\n<b>Network: </b>" + network + "\n<b>Distance off route (mi): </b>" + str(row['distance'])
        
        return text
    
    df['text'] = df.apply(build_station_text, axis=1)

    #TODO: change icon image to be logo based on network, maybe color too
    for idx, row in df.iterrows():
        Marker(
            row[['latitude', 'longitude']].values,
            icon=Icon(color='orange', icon='fa-solid fa-bolt', prefix='fa'),
            tooltip=row['text'] if tooltip else None,
            popup=row['text'],
            ).add_to(map)
        
    logger.info(
        "Counts of networks along the route: %s",
        df['ev_network'].value_counts()
    )
    
    return map