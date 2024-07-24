from typing import List, Dict, Union
from uuid import uuid4

from google.cloud import storage
from google.cloud import bigquery
import pandas as pd
import numpy as np

from evlens.logs import setup_logger
logger = setup_logger(__name__)


# Adapted from https://cloud.google.com/storage/docs/uploading-objects#storage-upload-object-python
def upload_file(
    bucket_name: str,
    source_filepath: str,
    destination_blob_name: str = None
):
    """Uploads a file to the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"
    # The path to your file to upload
    # source_file_name = "local/path/to/file"
    # The ID of your GCS object
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    if destination_blob_name is None:
        destination_blob_name = source_filepath
    blob = bucket.blob(destination_blob_name)

    # Optional: set a generation-match precondition to avoid potential race conditions
    # and data corruptions. The request to upload is aborted if the object's
    # generation number does not match your precondition. For a destination
    # object that does not yet exist, set the if_generation_match precondition to 0.
    # If the destination object already exists in your bucket, set instead a
    # generation-match precondition using its generation number.
    generation_match_precondition = 0

    blob.upload_from_filename(
        source_filepath,
        if_generation_match=generation_match_precondition
    )

    logger.info(
        "File %s uploaded to %s.",
        source_filepath,
        destination_blob_name
    )
    
    
def download_blob(
    bucket_name: str,
    source_blob_name: str,
    destination_file_name: str = None
):
    """Downloads a blob from the bucket."""
    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name"

    # The ID of your GCS object
    # source_blob_name = "storage-object-name"

    # The path to which the file should be downloaded
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    if destination_file_name is None:
        destination_file_name = source_blob_name
    blob.download_to_filename(destination_file_name)

    logger.info(
        "Downloaded storage object %s from bucket %s to local file %s.",
        source_blob_name,
        bucket_name,
        destination_file_name
    )
    

class BigQuery:
    '''
    Set of useful methods all tied to a single GCP project for BigQuery table setup, querying, data insertion, etc.
    '''
    def __init__(
        self,
        project: str = 'evlens',
        location: str = 'US'
    ):
        self.project = project
        self.location = location
        self.client = bigquery.Client(
            project=project,
            location=location
        )
        
    def _make_dataset_id(
        self,
        dataset_name: str
    ) -> str:
        return f"{self.project}.{dataset_name}"
    
    def _make_table_id(
        self,
        dataset: str,
        table: str
    ) -> str:
        dataset_id = self._make_dataset_id(dataset)
        return dataset_id + "." + table
        
    @classmethod
    def make_uuid(cls) -> str:
        return str(uuid4())
        
    def create_dataset(
        self,
        dataset: str,
        location: str = None
    ):
        dataset_id = self._make_dataset_id(dataset)
        # Construct a full Dataset object to send to the API.
        dataset = bigquery.Dataset(dataset_id)

        # Specify the geographic location where the dataset should reside.
        if location is None:
            location = self.client.location
        dataset.location = location

        # Send the dataset to the API for creation, with an explicit timeout.
        # Raises google.api_core.exceptions.Conflict if the Dataset already
        # exists within the project.
        dataset = self.client.create_dataset(dataset, timeout=30)  # Make an API request.
        logger.info("Created dataset %s.%s",
                    self.client.project,
                    dataset.dataset_id
        )
        
    def list_datasets(self) -> List[str]:
        
        datasets = list(self.client.list_datasets())  # Make an API request.
        project = self.client.project

        if datasets:
            logger.info(
                "Datasets in project %s: %s",
                project,
                [d.dataset_id for d in datasets]
            )
        else:
            logger.error("%s project does not contain any datasets.", project)
    
    def setup_table(
        self,
        dataset: str,
        table_name: str,
        schema_path: str
    ):
        
        table_id = self._make_table_id(dataset, table_name)
        schema = self.client.schema_from_json(schema_path)

        table = bigquery.Table(table_id, schema=schema)
        table = self.client.create_table(table)  # API request
        logger.info("Created table %s.", table_id)
        
    def set_table_keys(
        self,
        dataset: str,
        table: str,
        primary_key_columns: Union[str, List[str]],
        foreign_keys: List[Dict[str, str]] = None
    ):
        '''
        Sets primary and foreign keys on an existing table.

        Parameters
        ----------
        table : str
            Name of the table
        primary_key_columns : List[str]
            Columns in the table to use as the (composite) primary key
        foreign_keys : List[Dict[str, str]]
            Foreign key mappings, if any. Should be of the form:
            
            [
                {
                    'key': '<column>',
                    'foreign_table': '<foreign_table_name>',
                    'foreign_column': '<foreign_table_column_name>'
                },
                {...},
                ...
            ]
        '''
        table_id = self._make_table_id(dataset, table)
        
        if isinstance(primary_key_columns, str):
            primary_key_columns = [primary_key_columns]
        
        fk_subqueries = []
        if foreign_keys is not None:
            for d in foreign_keys:
                fk_subqueries.append(
                    f"ADD FOREIGN KEY({d['key']}) references {d['foreign_table']}({d['foreign_column']}) NOT ENFORCED"
                )
            foreign_key_subquery = ',\n'.join(fk_subqueries)
            
            query = f"""
            ALTER table {table_id} ADD primary key({', '.join(primary_key_columns)}) NOT ENFORCED,
            {foreign_key_subquery};
            """
            
        else:
            query = f"""
            ALTER table {table_id} ADD primary key({', '.join(primary_key_columns)}) NOT ENFORCED;
            """
        
        return self.client.query(query)
        # return query

    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        
        df = self.client.query_and_wait(query).to_dataframe()
        return df.replace({None: np.nan}).dropna(how='all')
    
    def insert_data(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        table_name: str,
        merge_columns: Union[str, List[str]] = None
    ):
        '''
        Inserts new data as an append operation to BQ. NOTE THAT BQ DOES NOT DE-DUPLICATE DATA, IT APPENDS BLINDLY. So use with caution.

        Parameters
        ----------
        df : pd.DataFrame
            The data of interest, DataFrame schema needs to match BQ table schema (but need not have columns in same order)
        dataset_name : str
            Name of the target BQ Dataset
        table_name : str
            Name of the target BQ table
        merge_columns : Union[str, List[str]]
            If this should be a merge operation in which only truly new rows should be added to BQ, set this to the column names in the BQ table (and thus also in `df`) that represent a unique composite key to use for de-duplication purposes. If not None, this will query BQ for all its data in the provided table before attempting to insert new data. If no new rows are detected in `df` after comparing to the contents of the table, insertion will be aborted.
        '''
        # Set table_id to the ID of the table to create.
        table_id = self._make_table_id(dataset_name, table_name)

        job = self.client.load_table_from_dataframe(
            df, table_id#, job_config=job_config
        )  # Make an API request.
        job.result()  # Wait for the job to complete.
        
        if merge_columns is not None:
            df = self.check_and_remove_duplicates(
                dataset_name,
                table_name,
                df,
                merge_columns
            )
            if df is None or df.empty:
                logger.error("No new rows detected in `df` when de-duplicating with columns %s, data insertion aborted", merge_columns)
                return

        table = self.client.get_table(table_id)  # Make an API request.
        logger.info(
            "Loaded %s rows and %s columns to %s",
            table.num_rows,
            len(table.schema),
            table_id
        )
        
    def clear_table(
        self,
        dataset_name: str,
        table_name: str
    ):
        
        table_id = self._make_table_id(dataset_name, table_name)
        query = f"DELETE FROM `{table_id}` WHERE true"
        self.client.query_and_wait(query)
        logger.info("Table %s cleared", table_id)
        
    def check_and_remove_duplicates(
        self,
        dataset_name: str,
        table_name: str,
        data: pd.DataFrame,
        unique_columns: Union[str, List[str]]
    ) -> pd.DataFrame:
        '''
        Checks a BigQuery table to determine what, if any, duplicate rows already exist relative to the provided `data` and returns a copy of `data` with the duplicate rows removed. Useful for ensuring only unique rows are added to BigQuery (but of course at the cost of some latency).

        Parameters
        ----------
        dataset_name : str
            Name of the target BQ Dataset
        table_name : str
            Name of the target BQ table
        data : pd.DataFrame
            DataFrame being checked for duplicates
        unique_columns : Union[str, List[str]]
            Column name(s) in the BQ table and `data` that are being used to de-duplicate (e.g. an `id` column or `id` and `timestamp`).

        Returns
        -------
        pd.DataFrame
            De-duplicated copy of `data`. If these data were to be inserted into BigQuery, would result in totally new rows.
        '''
        data = data.drop_duplicates(subset=unique_columns)
        
        # Can get 
        if isinstance(unique_columns, str):
            query = f"SELECT DISTINCT {unique_columns} FROM {self._make_table_id(dataset_name, table_name)}"
            unique_columns = [unique_columns]
            
        else:
            query = f"SELECT * FROM {self._make_table_id(dataset_name, table_name)}"
        
        logger.info("Querying table...")
        table_data = self.query_to_dataframe(query).drop_duplicates(subset=unique_columns)
        logger.info("Table query done")
        
        # Add a column to use as a known merged column name for de-dupe
        extra_column = [c for c in data.columns if c not in unique_columns][0]
        table_data[extra_column] = ''
        
        # Filter for only those rows that did not successfully merge to table
        results = data[data.merge(table_data, how='left', on=unique_columns)[extra_column + '_y'].isnull()]
        
        if results.empty:
            logger.warning("No new data present")
            return None
        
        return results