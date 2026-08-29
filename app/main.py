from pathlib import Path
from uuid import uuid4

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    BackgroundTasks,
)
from fastapi.staticfiles import StaticFiles

from app.services.clipping import create_clips
from app.services.downloader import download_video
from app.services.highlight import find_highlights
from app.services.video import extract_audio


app = FastAPI(
    title="GenTe",
)


# Directories
UPLOAD_DIR = Path("uploads")
AUDIO_DIR = Path("audio")
CLIPS_DIR = Path("clips")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

AUDIO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CLIPS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# Serve generated clips
app.mount(
    "/clips",
    StaticFiles(directory=str(CLIPS_DIR)),
    name="clips",
)


# In-memory status store
tasks_status = {}


def process_video_pipeline(
    video_id: str,
    video_path: Path,
    audio_path: Path,
    url: str | None,
    prompt: str,
    filename: str,
):
    try:
        # 1. Download video if URL is provided
        if url:
            tasks_status[video_id] = {
                "status": "processing",
                "progress": "downloading",
                "filename": filename,
                "clips": [],
            }
            download_video(
                url=url,
                output_path=str(video_path),
            )

        # 2. Extract Audio
        tasks_status[video_id] = {
            "status": "processing",
            "progress": "extracting_audio",
            "filename": filename,
            "clips": [],
        }
        extract_audio(
            str(video_path),
            str(audio_path),
        )

        # 3. Find Highlights (Directly from audio)
        tasks_status[video_id] = {
            "status": "processing",
            "progress": "finding_highlights",
            "filename": filename,
            "clips": [],
        }
        highlights = find_highlights(
            str(audio_path),
            prompt,
        )

        # 4. Create Clips
        tasks_status[video_id] = {
            "status": "processing",
            "progress": "clipping",
            "filename": filename,
            "clips": [],
        }
        clips_data = create_clips(
            str(video_path),
            highlights,
        )

        # 5. Completed
        tasks_status[video_id] = {
            "status": "completed",
            "progress": "done",
            "filename": filename,
            "clips": clips_data["clips"],
            "merged_clip_url": clips_data["merged_clip_url"],
        }

    except Exception as exc:
        tasks_status[video_id] = {
            "status": "failed",
            "error": str(exc),
            "filename": filename,
            "clips": [],
            "merged_clip_url": None,
        }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/videos/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    prompt: str = Form(
        "Summarize the video in 3 sentences."
    ),
):
    """
    Create video highlights from either:

    - an uploaded video file
    - a video URL
    """

    # Validate input
    if file is not None and url:
        raise HTTPException(
            status_code=400,
            detail="Provide either a video file or a URL, not both.",
        )

    if file is None and not url:
        raise HTTPException(
            status_code=400,
            detail="Provide a video file or a video URL.",
        )

    video_id = uuid4().hex

    video_path = (
        UPLOAD_DIR /
        f"{video_id}.mp4"
    )

    audio_path = (
        AUDIO_DIR /
        f"{video_id}.mp3"
    )

    filename = ""

    # CASE 1: Uploaded video
    if file is not None:
        allowed_extensions = {
            ".mp4",
            ".mov",
            ".mkv",
            ".webm",
        }

        original_filename = (
            file.filename or ""
        )

        extension = Path(
            original_filename
        ).suffix.lower()

        if extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported video format. "
                    "Supported formats: "
                    ".mp4, .mov, .mkv, .webm"
                ),
            )

        # Save the uploaded video locally
        with video_path.open("wb") as output_file:
            while True:
                chunk = await file.read(
                    1024 * 1024
                )
                if not chunk:
                    break
                output_file.write(chunk)

        filename = original_filename

    # CASE 2: Video URL
    else:
        filename = url

    # Start the background task
    background_tasks.add_task(
        process_video_pipeline,
        video_id,
        video_path,
        audio_path,
        url,
        prompt,
        filename,
    )

    # Initialize status in the dictionary
    tasks_status[video_id] = {
        "status": "processing",
        "progress": "queued",
        "filename": filename,
        "clips": [],
        "merged_clip_url": None,
    }

    return {
        "video_id": video_id,
        "status": "processing",
        "check_status_url": f"/videos/{video_id}"
    }


@app.get("/videos/{video_id}")
def get_video_status(video_id: str):
    """
    Get the status of a highlight generation task.
    """
    if video_id not in tasks_status:
        raise HTTPException(
            status_code=404,
            detail="Video task not found."
        )

    return tasks_status[video_id]