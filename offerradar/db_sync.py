# offerradar/db_sync.py
import boto3
from botocore.exceptions import ClientError


def download_file(bucket: str, key: str, local_path: str) -> bool:
    """Download a file from S3. Returns False if the key does not exist (first run)."""
    s3 = boto3.client("s3")
    try:
        s3.download_file(bucket, key, local_path)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def upload_file(bucket: str, key: str, local_path: str) -> None:
    s3 = boto3.client("s3")
    s3.upload_file(local_path, bucket, key)
