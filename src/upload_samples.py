import os
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:8333")
BUCKET = os.getenv("S3_BUCKET", "incoming")

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=os.environ["S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    region_name="us-east-1",
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)


def ensure_bucket() -> None:
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=BUCKET)


def count_objects() -> int:
    total = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET):
        total += len(page.get("Contents", []))
    return total


def main() -> None:
    ensure_bucket()
    files = sorted(Path("data/samples").glob("*.pdf"))
    for f in files:
        s3.upload_file(str(f), BUCKET, f.name)
    print(f"{len(files)} fichiers envoyés, {count_objects()} présents dans s3://{BUCKET}")


if __name__ == "__main__":
    main()
