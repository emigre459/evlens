from typing import List, Union
import os

from roadtrip.logs import setup_logger
logger = setup_logger(__name__, send_to_gcp=False)

import requests
import pandas as pd

class AFDC:
    '''
    A data retrieval class for NREL's Alternative Fuels Data Center, tuned to be EV-specific. See https://developer.nrel.gov/docs/transportation/alt-fuel-stations-v1/ for more information.
    '''
    def __init__(
        self
    ):
        pass
    
    def _str_list_to_url_component(self, l: Union[str, List[str]]) -> str:
        if isinstance(l, str):
            return l
        elif len(l) > 1:
            return ",".join(l)
        else:
            return l[0]
    
    def _build_url(
        self,
        status: List[str],
        access: str,
        fuel_type: List[str],
        ev_charging_level: List[str],
        ev_connector_type: List[str]
    ) -> str:
        base_url = 'https://developer.nrel.gov/api/alt-fuel-stations/v1.json?'
        
        url = base_url \
            + "status=" + self._str_list_to_url_component(status) \
            + "&access=" + access \
            + "&fuel_type=" + self._str_list_to_url_component(fuel_type) \
            + "&ev_charging_level=" + self._str_list_to_url_component(ev_charging_level) \
            + "&ev_connector_type=" + self._str_list_to_url_component(ev_connector_type)
            
        return url
    
    def get_stations(
        self,
        status: Union[str, List[str]] = 'E',
        access: str = 'public',
        fuel_type: Union[str, List[str]] = 'ELEC',
        ev_charging_level: Union[str, List[str]] = ['3', 'dc_fast'],
        ev_connector_type: Union[str, List[str]] = ['J1772COMBO', 'CHADEMO', 'TESLA'],
        api_key: str = None,
        limit: int = None
    ) -> pd.DataFrame:
        
        if api_key is None:
            api_key = os.getenv('NREL_API_KEY', None)
        headers = {'x-api-key': api_key}
        
        url = self._build_url(
            status=status,
            access=access,
            fuel_type=fuel_type,
            ev_charging_level=ev_charging_level,
            ev_connector_type=ev_connector_type
        )
        
        if limit is not None and limit > 0 and isinstance(limit, int):
            url += "&limit=" + str(limit)
        
        response = requests.get(
            url,
            headers=headers
        )
        
        results = response.json()
        
        if response.ok:
            logger.info(
                "%s total records found, comprised of %s plugs",
                results['total_results'],
                results['station_counts']['total']
            )
        
        return pd.DataFrame(results['fuel_stations'])