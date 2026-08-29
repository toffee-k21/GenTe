import boto3

from app.config import (
    AWS_REGION,
    USERS_TABLE_NAME,
    VIDEOS_TABLE_NAME
)


dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)


users_table = dynamodb.Table(
    USERS_TABLE_NAME
)


videos_table = dynamodb.Table(
    VIDEOS_TABLE_NAME
)