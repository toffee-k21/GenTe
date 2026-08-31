from pathlib import Path
from uuid import uuid4
from fastapi.staticfiles import StaticFiles
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Form,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware

from app.services.clipping import create_clips, merge_clips
from app.services.highlight import find_highlights
from app.services.video import extract_audio
from app.services.transcription import (
    transcribe_audio,
)
from app.services.youtube import download_youtube_video
from app.auth import router as auth_router, get_current_user
from app.services.video_save import (
    save_generated_video,
    get_user_videos,
    get_private_videos,
    get_public_videos,
    get_video,
    change_video_visibility,
)
from app.schemas.video import VideoVisibilitySchema

app = FastAPI(
    title="TeaserAI",
)

app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://teaserai.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/clips",
    StaticFiles(directory="clips"),
    name="clips",
)

UPLOAD_DIR = Path("uploads")
AUDIO_DIR = Path("audio")


UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    prompt: str = Form("Summarize the video in 3 sentences."),
    current_user: str = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing",
        )

    extension = Path(file.filename).suffix.lower()
    allowed_extensions = {
        ".mp4",
        ".mov",
        ".mkv",
        ".webm",
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format",
        )

    video_id = uuid4().hex
    video_filename = f"{video_id}{extension}"
    video_path = UPLOAD_DIR / video_filename
    filename_to_return = file.filename

    print(f"[STAGE: File Upload] Started saving file: {filename_to_return}")
    try:
        with open(video_path, "wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
        print(f"[STAGE: File Upload] SUCCESS. Saved to {video_path}")
    except Exception as e:
        print(f"[STAGE: File Upload] FAILURE: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

    return await process_video_pipeline(video_id, video_path, filename_to_return, prompt)


@app.post("/videos/youtube")
async def youtube_video(
    youtube_url: str = Form(...),
    prompt: str = Form("Summarize the video in 3 sentences."),
    current_user: str = Depends(get_current_user),
):
    video_id = uuid4().hex
    print(f"[STAGE: YouTube Download] Started for URL: {youtube_url}")
    try:
        downloaded_file_path = download_youtube_video(youtube_url, UPLOAD_DIR, video_id)
        video_path = Path(downloaded_file_path)
        extension = video_path.suffix.lower()
        filename_to_return = f"youtube_{video_id}{extension}"
        print(f"[STAGE: YouTube Download] SUCCESS. Video saved to {video_path}")
    except Exception as e:
        print(f"[STAGE: YouTube Download] FAILURE: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to download YouTube video: {str(e)}"
        )

    return await process_video_pipeline(video_id, video_path, filename_to_return, prompt)


async def process_video_pipeline(
    video_id: str,
    video_path: Path,
    filename_to_return: str,
    prompt: str,
):

    # ========================================================
    # 1. Extract audio
    # ========================================================

    audio_filename = f"{video_id}.mp3"
    audio_path = AUDIO_DIR / audio_filename

    print("[STAGE: Audio Extraction] Started")

    try:
        extract_audio(
            str(video_path),
            str(audio_path),
        )

        print("[STAGE: Audio Extraction] SUCCESS")

    except Exception as e:
        print(f"[STAGE: Audio Extraction] FAILURE: {str(e)}")
        raise e


    # ========================================================
    # 2. Find highlights
    # ========================================================

    print("[STAGE: Highlights Analysis] Started")

    try:
        highlights = find_highlights(
            str(audio_path),
            prompt,
        )

        print("[STAGE: Highlights Analysis] SUCCESS")

        # Audio no longer needed
        delete_file(audio_path)

    except Exception as e:
        print(f"[STAGE: Highlights Analysis] FAILURE: {str(e)}")
        raise e


    print("Highlights found:", highlights)


    # ========================================================
    # 3. Create clips
    # ========================================================

    print("[STAGE: Video Clipping] Started")

    try:
        clips = create_clips(
            str(video_path),
            highlights,
        )

        print("[STAGE: Video Clipping] SUCCESS")

        # Original uploaded video no longer needed
        delete_file(video_path)

    except Exception as e:
        print(f"[STAGE: Video Clipping] FAILURE: {str(e)}")
        raise e


    # ========================================================
    # 4. Merge clips into teaser
    # ========================================================

    print("[STAGE: Teaser Generation/Merge] Started")

    try:
        teaser_url = merge_clips(
            video_id,
            clips,
        )

        print("[STAGE: Teaser Generation/Merge] SUCCESS")

        # Delete temporary clips
        for clip in clips:
            delete_file(Path(clip))

    except Exception as e:
        print(f"[STAGE: Teaser Generation/Merge] FAILURE: {str(e)}")
        raise e


    # ========================================================
    # 5. Return teaser
    # ========================================================

    return {
        "video_id": video_id,
        "filename": filename_to_return,
        # "clips": clips,
        "teaser_url": teaser_url,
    }


@app.post("/{video_id}/save")
async def save_video(
    video_id: str,

    visibility: VideoVisibilitySchema,

    current_user=Depends(
        get_current_user
    ),
):

    user_id = current_user["user_id"]

    teaser_path = (
        Path("clips")
        / video_id
        / "teaser.mp4"
    )

    if not teaser_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Generated video not found",
        )

    try:

        result = save_generated_video(

            user_id=user_id,

            video_id=video_id,

            teaser_path=str(
                teaser_path
            ),

            visibility=visibility.visibility,
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save video: {str(e)}",
        )

    # Delete local copy after successful S3 upload
    try:

        teaser_path.unlink(
            missing_ok=True
        )

    except Exception:
        pass

    return result

@app.get("/my")
async def my_videos(
    current_user=Depends(
        get_current_user
    ),
):

    user_id = current_user["user_id"]

    videos = get_user_videos(
        user_id
    )

    return {
        "videos": videos
    }

@app.get("/private")
async def private_videos(
    current_user=Depends(
        get_current_user
    ),
):

    user_id = current_user["user_id"]

    videos = get_private_videos(
        user_id
    )

    return {
        "videos": videos
    }

@app.get("/public")
async def public_videos():

    videos = get_public_videos()

    return {
        "videos": videos
    }

@app.patch("/{video_id}/visibility")
async def update_visibility(
    video_id: str,

    visibility: VideoVisibilitySchema,

    current_user=Depends(
        get_current_user
    ),
):

    user_id = current_user["user_id"]

    # Check that this video belongs to user
    video = get_video(
        user_id=user_id,
        video_id=video_id,
    )

    if not video:

        raise HTTPException(
            status_code=404,
            detail="Video not found",
        )

    if video.get("status") != "saved":

        raise HTTPException(
            status_code=400,
            detail="Video has not been saved",
        )

    # Update visibility
    updated_video = change_video_visibility(

        user_id=user_id,

        video_id=video_id,

        visibility=visibility.visibility,
    )

    return {
        "message": "Video visibility updated",
        "video": updated_video,
    }

def delete_file(path: Path):
    try:
        path.unlink(missing_ok=True)
        print(f"[CLEANUP] Deleted: {path}")
    except Exception as e:
        print(f"[CLEANUP] Failed to delete {path}: {e}")