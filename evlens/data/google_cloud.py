from evlens.logs import setup_logger
logger = setup_logger(__name__)

from google.cloud import storage


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
