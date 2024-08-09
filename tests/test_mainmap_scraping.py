from roadtrip.data.plugshare import MainMapScraper

# Electrify America in Springfield, VA mall parking lot
TEST_LOCATION = '252784'

from roadtrip.logs import setup_logger
logger = setup_logger(__name__)

from datetime import date
TODAY_STRING = date.today().strftime("%m-%d-%Y")


if __name__ == '__main__':
    s = MainMapScraper(
        f"data/external/plugshare/{TODAY_STRING}/",
        timeout=3,
        progress_bars=True,
        headless=True
    )
    df_locations, df_checkins = s.run([TEST_LOCATION, TEST_LOCATION])
    
    assert not df_locations.empty, "Location metadata empty"
    assert not df_checkins.empty, "No checkins found"
    # df_locations.to_pickle('df_locations.pkl')
    # df_checkins.to_pickle('df_checkins.pkl')
    print("SUCCESS!")