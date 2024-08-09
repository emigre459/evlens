from roadtrip.data.google_cloud import BigQuery

from roadtrip.logs import setup_logger
logger = setup_logger(__name__)

if __name__ == '__main__':
    bq = BigQuery()
    query = f"""
    SELECT *
    FROM `{bq._make_table_id('plugshare', 'locationID')}`
    LIMIT 10
    """
    df = bq.query_to_dataframe(query)
    
    assert len(df) == 10, "Why are we missing data, should be 10"
    assert 'location_id' in df.columns, "Missing location_id column"