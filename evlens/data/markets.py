import pandas as pd
from rich import print


# NOTE: these numbers aren't perfect as they are quickly derived w/ assumption 
# that you can just take out the DC charging amount evenly from DC-only 
# estimates when doing mixed L2 + DC
DC_PLUG_MONTHLY_REVENUE_LOW = 2640.00 / 2
DC_PLUG_MONTHLY_REVENUE_HIGH = 10560.00 / 2
# 2x AC and 1X DC charges per day w/ 4x AC plugs
L2_PLUG_MONTHLY_REVENUE_LOW = 3000 * 0.67 / 4
# 4x AC and 2X DC charges per day w/ 4x AC plugs
L2_PLUG_MONTHLY_REVENUE_HIGH = 6000 * 0.67 / 4

# Evenly between
DC_PLUG_MONTHLY_REVENUE_MEDIUM = \
    (DC_PLUG_MONTHLY_REVENUE_HIGH - DC_PLUG_MONTHLY_REVENUE_LOW) / 2 + DC_PLUG_MONTHLY_REVENUE_LOW
L2_PLUG_MONTHLY_REVENUE_MEDIUM = \
    (L2_PLUG_MONTHLY_REVENUE_HIGH - L2_PLUG_MONTHLY_REVENUE_LOW) / 2 + L2_PLUG_MONTHLY_REVENUE_LOW


def clean_adfc_charging_stations_data(
    filepath: str,
    include_level2: bool = True,
    revenue_loss_plug_fraction: float = 0.25,
    annual_revenue_estimate_per_dc_plug: float = DC_PLUG_MONTHLY_REVENUE_MEDIUM * 12,
    annual_revenue_estimate_per_level2_plug: float = L2_PLUG_MONTHLY_REVENUE_MEDIUM * 12,
    num_plugs_per_station_dc: int = 4,
    num_plugs_per_station_level2: int = 4,
) -> pd.DataFrame:
    
    # Including level 2 chargers suggests monthly revenue of $3000 (2 DC chargers + 4 AC)
    # or $90/month for each AC charger
    df = pd.read_csv(filepath)
    df = df[(df['Fuel Type Code'] == 'ELEC') & (df['Country'] == 'US')]
        
    if include_level2:
        columns_of_interest = ['EV DC Fast Count', 'EV Level2 EVSE Num']
    else:
        columns_of_interest = ['EV DC Fast Count']
        
    plug_counts_by_network = df.dropna(subset=columns_of_interest, how='all')\
        .groupby('EV Network')[columns_of_interest].sum().reset_index()
    plug_counts_by_network['Total'] = \
        plug_counts_by_network[columns_of_interest].sum(axis=1).astype(int)
    # dc_plug_counts_by_network.drop(columns=columns_of_interest, inplace=True)
        
    non_tesla_plugs = plug_counts_by_network[
        ~plug_counts_by_network['EV Network'].str.contains('Tesla')
    ]
    tesla_plugs = plug_counts_by_network[
        plug_counts_by_network['EV Network'].str.contains('Tesla')
    ]
    
    print(f"Number of Tesla plugs: {tesla_plugs['Total'].sum():,}")
    print(f"Number of non-Tesla plugs: {non_tesla_plugs['Total'].sum():,}")
    
    # How much revenue across an arbitrary # of stations?
    # Assume (non-Tesla) 4x plugs per station and $2,640 of monthly recurring 
    # revenue per station 
    # https://blog.evbox.com/make-money-ev-charging-stations#:~:text=EV%20charging%20station%20revenue%20overview
    if include_level2:
        non_tesla_annual_revenue = \
            non_tesla_plugs['EV Level2 EVSE Num'].sum() * annual_revenue_estimate_per_level2_plug \
                + non_tesla_plugs['EV DC Fast Count'].sum() * annual_revenue_estimate_per_dc_plug
    else:
        non_tesla_annual_revenue = \
            non_tesla_plugs['EV DC Fast Count'].sum() * annual_revenue_estimate_per_dc_plug
    print(f"2023 Non-Tesla Revenue: ${non_tesla_annual_revenue:,}")
    print(f"2023 Non-Tesla Revenue Lost: ${non_tesla_annual_revenue*revenue_loss_plug_fraction:,}")
    
    # What will this number of lost revenue be in 2030 when we have more DCFC public plugs?
    # https://www.mckinsey.com/features/mckinsey-center-for-future-mobility/our-insights/can-public-ev-fast-charging-stations-be-profitable-in-the-united-states
    # Assume 4 plugs per station, similar proportion of non-Tesla-to-Tesla station counts
    non_tesla_fraction = non_tesla_plugs['Total'].sum() / plug_counts_by_network['Total'].sum()
    print(f"{non_tesla_fraction=}")
    
    public_plug_multiplier_2030 = 1.5/0.1 # need multiplier since plug counts don't line up with McK estimate
    
    plug_count_2030 = public_plug_multiplier_2030 * plug_counts_by_network['Total'].sum()
    print(f"{plug_count_2030=:,}")
    print(f"Expected number of non-Tesla stations in US by 2030: {non_tesla_fraction * plug_count_2030 / 4:,}")
    non_tesla_plugs_annual_revenue_2030 = public_plug_multiplier_2030 * non_tesla_annual_revenue
    
    # DCFC stats
    print(f"2030 non-Tesla revenue by 2030: ${non_tesla_plugs_annual_revenue_2030:,}")
    print(f"Lost 2030 non-Tesla revenue due to down plugs: ${non_tesla_plugs_annual_revenue_2030*revenue_loss_plug_fraction:,}")
    
    return df
    