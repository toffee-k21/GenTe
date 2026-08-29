import boto3

from app.config import (
    AWS_REGION,
    S3_BUCKET_NAME
)


s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)


def upload_file(
    file_obj,
    s3_key: str,
    content_type: str
):
    s3.upload_fileobj(
        file_obj,
        S3_BUCKET_NAME,
        s3_key,
        ExtraArgs={
            "ContentType": content_type
        }
    )


def delete_file(s3_key: str):

    s3.delete_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key
    )


def generate_presigned_url(
    s3_key: str,
    expires_in: int = 3600
):

    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": S3_BUCKET_NAME,
            "Key": s3_key
        },
        ExpiresIn=expires_in
    )