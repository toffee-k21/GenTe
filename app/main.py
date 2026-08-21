from pathlib import Path
from uuid import uuid4
from fastapi.staticfiles import StaticFiles
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,

)

from app.services.clipping import create_clips
from app.services.highlight import find_highlights
from app.services.video import extract_audio
from app.services.transcription import (
    transcribe_audio,
)


app = FastAPI(
    title="GenTe",
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


@app.post("/videos")
async def upload_video(
    file: UploadFile = File(...),
    prompt: str = "Summarize the video in 3 sentences.",
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing",
        )


    extension = Path(
        file.filename
    ).suffix.lower()

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

# save video
    video_filename = (
        f"{video_id}{extension}"
    )

    video_path = (
        UPLOAD_DIR /
        video_filename
    )

    with open(
        video_path,
        "wb",
    ) as output:

        while chunk := await file.read(
            1024 * 1024
        ):

            output.write(chunk)

# extract audio
    audio_filename = (
        f"{video_id}.mp3"
    )

    audio_path = (
        AUDIO_DIR /
        audio_filename
    )

    extract_audio(
        str(video_path),
        str(audio_path),
    )

#transcript
    transcript = transcribe_audio(
        str(audio_path)
    )


#highlight
    highlights = find_highlights(
        transcript,
        prompt
    )

    print("Highlights found:", highlights)

#clip
    clips = create_clips(
        str(video_path),
        highlights
    )

    return {
        "video_id": video_id,

        "filename": file.filename,

        "clips": clips
    }