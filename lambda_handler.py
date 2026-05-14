# lambda_handler.py
import json
import os
import tempfile
from offerradar.db_sync import download_file, upload_file
from main import run_pipeline

S3_BUCKET = os.environ["S3_BUCKET"]
DB_KEY = "jobs.db"
RESUME_KEY = "resume.pdf"


def handler(event, context):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = f"{tmp}/jobs.db"
        resume_path = f"{tmp}/resume.pdf"

        print("Downloading state from S3...")
        download_file(S3_BUCKET, DB_KEY, db_path)
        if not download_file(S3_BUCKET, RESUME_KEY, resume_path):
            raise RuntimeError(
                "resume.pdf not found in S3 — upload it first with: "
                f"aws s3 cp resume.pdf s3://{S3_BUCKET}/resume.pdf"
            )

        try:
            run_pipeline(db_path=db_path, resume_path=resume_path, use_unseen=True)
        finally:
            print("Uploading jobs.db to S3...")
            upload_file(S3_BUCKET, DB_KEY, db_path)

    return {"statusCode": 200, "body": json.dumps("Pipeline complete")}
