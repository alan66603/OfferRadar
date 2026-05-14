# tests/test_db_sync.py
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from offerradar.db_sync import download_file, upload_file


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": ""}}, "op")


def test_download_returns_true_on_success():
    mock_s3 = MagicMock()
    with patch("offerradar.db_sync.boto3.client", return_value=mock_s3):
        result = download_file("bucket", "jobs.db", "/tmp/jobs.db")
    assert result is True
    mock_s3.download_file.assert_called_once_with("bucket", "jobs.db", "/tmp/jobs.db")


def test_download_returns_false_on_404():
    mock_s3 = MagicMock()
    mock_s3.download_file.side_effect = _client_error("404")
    with patch("offerradar.db_sync.boto3.client", return_value=mock_s3):
        result = download_file("bucket", "jobs.db", "/tmp/jobs.db")
    assert result is False


def test_download_raises_on_other_errors():
    mock_s3 = MagicMock()
    mock_s3.download_file.side_effect = _client_error("403")
    with patch("offerradar.db_sync.boto3.client", return_value=mock_s3):
        raised = False
        try:
            download_file("bucket", "jobs.db", "/tmp/jobs.db")
        except ClientError:
            raised = True
    assert raised


def test_upload_calls_s3_correctly():
    mock_s3 = MagicMock()
    with patch("offerradar.db_sync.boto3.client", return_value=mock_s3):
        upload_file("bucket", "jobs.db", "/tmp/jobs.db")
    mock_s3.upload_file.assert_called_once_with("/tmp/jobs.db", "bucket", "jobs.db")
