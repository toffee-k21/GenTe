import os

from dotenv import load_dotenv


load_dotenv()

# -- gemini --
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set"
    )


# -- JWT --
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-secret-in-production"
)

JWT_ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)


# -- AWS --
AWS_REGION = os.getenv(
    "AWS_REGION",
    "ap-south-1"
)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


# -- DynamoDB --
USERS_TABLE_NAME = os.getenv(
    "USERS_TABLE_NAME",
    "users"
)

VIDEOS_TABLE_NAME = os.getenv(
    "VIDEOS_TABLE_NAME",
    "videos"
)

VIDEO_EMAIL_INDEX = "email-index"

VIDEO_PUBLIC_INDEX = "visibility-created_at-index"

VIDEO_ID_INDEX = "video_id-index"


# -- S3 --
S3_BUCKET_NAME = os.getenv(
    "S3_BUCKET_NAME"
)