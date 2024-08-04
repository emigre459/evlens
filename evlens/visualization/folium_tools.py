from typing import List, Dict, Union, Sequence, Tuple
import os

import pandas as pd
import numpy as np

from folium import Map, Marker, Icon, PolyLine
from shapely.geometry import LineString

from evlens.logs import setup_logger
logger = setup_logger(__name__)

MOBILE_PIXEL_SIZE = (360, 640) # width, height


def change_map_center(
    map: Map,
    center_coordinates: Sequence[float] = None, # should be lat, long
    route_coordinates: Sequence[Sequence[float]] = None,
    route_linestring: LineString = None
):
    if center_coordinates is None:
        if route_coordinates is not None and route_linestring is None:
            route_linestring = LineString([list(reversed(coord)) for coord in route_coordinates])
        
        center_coordinates = tuple(reversed(tuple(route_linestring.centroid.coords)[0]))
        
    map.location = center_coordinates
    

def get_single_point(
    coordinates: Sequence[float], # should be lat, long
    location_name: str,
    popup: bool = True,
    tooltip: bool = False,
    starting_zoom: int = 16,
    map_size: Tuple[int, int] = MOBILE_PIXEL_SIZE,
    include_zoom_widget: bool = True,
    map_tiles: str = 'OpenStreetMap',
    show_start_pin: bool = False
) -> Map:
    map = Map(
        location=coordinates,
        zoom_start=starting_zoom,
        tiles=map_tiles,
        # tiles='https://api.mapbox.com/styles/v1/mapbox/outdoors-v12/static/{y},{x},{z},0/300x200?access_token=' + os.getenv('MAPBOX_API_KEY'),
        # attr='Mapbox Attribution',
        # tiles='OpenTopoMap',
        width=map_size[0],
        height=map_size[1],
        zoom_control=include_zoom_widget
    )
    
    if show_start_pin:
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
    route_coordinates: Sequence[Sequence[float]],
    starting_zoom: int = 7,
    map_size: Tuple[int, int] = MOBILE_PIXEL_SIZE,
    map_tiles: str = 'OpenStreetMap',
    include_zoom_widget: bool = True,
    show_start_pin: bool = False
) -> Map:
    
    start_icon = Icon(color='green', icon='fa-solid fa-play', prefix='fa')
    end_icon = Icon(color='blue', icon='fa-solid fa-stop', prefix='fa')
    
    map = Map(
        location=start_coordinates,
        zoom_start=starting_zoom,
        width=map_size[0],
        height=map_size[1],
        zoom_control=include_zoom_widget,
        tiles=map_tiles
    )
    if show_start_pin:
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
    
    PolyLine(
        locations=route_coordinates,
        color='blue',
        weight=4,
        tooltip="Naive no-charging route",
        smooth_factor=2.0    
    ).add_to(map)
    
    # Center off of the route
    change_map_center(map, route_coordinates=route_coordinates)
    
    return map

def add_stations_to_map(
    data: pd.DataFrame,
    map: Map,
    stations_to_use: List[int],
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

        text = station_name \
            + "<br>" + address_string \
            + "<br><br><b>Network: </b>" + network \
            + "<br><b>Number of DCFC Plugs: </b>" + str(row['ev_dc_fast_num']) \
            + "<br><b>Distance off route (mi): </b>" + str(row['distance']) \
            + "<br>id=" + str(row['id'])
            
        # if 'distance_from_start' in df.columns:
        #     text += "<br><b>Distance from route start: </b>" + str(row['distance_from_start'])
            
        # if 'index' in df.columns:
        #     text += "<br><b>Index: </b>" + str(row['index'])
        
        if 'reliability_score' in df.columns:
            text += "<br><br><b>Reliability Score: " + str(row['reliability_score'])
        
        return text
    
    df['text'] = df.apply(build_station_text, axis=1)

    #TODO: change icon image to be logo based on network, maybe color too
    score_to_color = {
        1.0: 'green',
        0.5: 'orange',
        0.1: 'red',
        0.0: 'red'
    }
    df['reliability_score'].fillna(0)
    
    #TODO: fa-solid fa-bolt for backup stations, fa-solid fa-battery-<full|half|three-quarters|one-quarter> based on amount to charge up
    i = 0
    for _, row in df[df['id'].isin(stations_to_use)].iterrows():
        Marker(
            row[['latitude', 'longitude']].values,
            # icon=Icon(color='orange', icon='fa-solid fa-bolt', prefix='fa'),
            icon=Icon(color=score_to_color[row['reliability_score']], icon='fa-solid fa-battery-full', prefix='fa'),
            tooltip=row['text'] if tooltip else None,
            popup=row['text'],
            ).add_to(map)
        i += 1
        
    logger.info(
        "Counts of networks along the route: %s",
        df['ev_network'].value_counts()
    )
    
    return map