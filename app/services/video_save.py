from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.clients.dynamodb import videos_table

from app.clients.s3 import (
    upload_file,
    generate_presigned_url,
)


# ============================================================
# Save generated video
# ============================================================

def save_generated_video(
    user_id: str,
    video_id: str,
    teaser_path: str,
    visibility: str,
):

    s3_key = (
        f"videos/{user_id}/{video_id}.mp4"
    )

    # Upload local teaser to S3
    upload_file(
        file_path=teaser_path,
        s3_key=s3_key,
    )

    # Save metadata
    video_item = {
        "user_id": user_id,
        "video_id": video_id,
        "s3_key": s3_key,
        "visibility": visibility,
        "status": "saved",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    videos_table.put_item(
        Item=video_item
    )

    # Generate URL for immediate frontend use
    video_url = generate_presigned_url(
        s3_key=s3_key,
        expires_in=3600,
    )

    return {
        "video_id": video_id,
        "s3_key": s3_key,
        "visibility": visibility,
        "status": "saved",
        "video_url": video_url,
    }


# ============================================================
# Get one video
# ============================================================

def get_video(
    user_id: str,
    video_id: str,
):

    response = videos_table.get_item(
        Key={
            "user_id": user_id,
            "video_id": video_id,
        }
    )

    return response.get("Item")


# ============================================================
# Get user's videos
# ============================================================

def get_user_videos(
    user_id: str,
):

    response = videos_table.query(
        KeyConditionExpression=Key(
            "user_id"
        ).eq(user_id),

        ScanIndexForward=False,
    )

    videos = []

    for video in response.get(
        "Items",
        [],
    ):

        if video.get("status") != "saved":
            continue

        video["video_url"] = generate_presigned_url(
            s3_key=video["s3_key"],
            expires_in=3600,
        )

        videos.append(video)

    return videos


# ============================================================
# Get private videos
# ============================================================

def get_private_videos(
    user_id: str,
):

    response = videos_table.query(
        KeyConditionExpression=Key(
            "user_id"
        ).eq(user_id),

        ScanIndexForward=False,
    )

    videos = []

    for video in response.get(
        "Items",
        [],
    ):

        if video.get("status") != "saved":
            continue

        if video.get("visibility") != "private":
            continue

        videos.append({
            "video_id": video["video_id"],
            "visibility": video["visibility"],
            "created_at": video["created_at"],
            "video_url": generate_presigned_url(
                s3_key=video["s3_key"],
                expires_in=3600,
            ),
        })

    return videos


# ============================================================
# Get all public videos
# ============================================================

def get_public_videos():

    response = videos_table.query(
        IndexName="visibility-created_at-index",

        KeyConditionExpression=Key(
            "visibility"
        ).eq("public"),

        ScanIndexForward=False,
    )

    videos = []

    for video in response.get(
        "Items",
        [],
    ):

        if video.get("status") != "saved":
            continue

        videos.append({
            "video_id": video["video_id"],
            "user_id": video["user_id"],
            "visibility": video["visibility"],
            "created_at": video["created_at"],
            "video_url": generate_presigned_url(
                s3_key=video["s3_key"],
                expires_in=3600,
            ),
        })

    return videos


# ============================================================
# Change visibility
# ============================================================

def change_video_visibility(
    user_id: str,
    video_id: str,
    visibility: str,
):

    response = videos_table.update_item(

        Key={
            "user_id": user_id,
            "video_id": video_id,
        },

        UpdateExpression=(
            "SET #visibility = :visibility"
        ),

        ExpressionAttributeNames={
            "#visibility": "visibility",
        },

        ExpressionAttributeValues={
            ":visibility": visibility,
        },

        ReturnValues="ALL_NEW",
    )

    return response.get(
        "Attributes"
    )