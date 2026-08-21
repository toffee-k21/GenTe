from pathlib import Path
import subprocess


CLIPS_DIR = Path("clips")

CLIPS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def create_clips(
    video_path: str,
    highlights: dict,
):
    video_id = Path(video_path).stem

    video_clips_dir = CLIPS_DIR / video_id

    video_clips_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    clips = []

    for index, highlight in enumerate(
        highlights["clips"],
        start=1,
    ):
        start = highlight["start"]
        end = highlight["end"]

        duration = end - start

        clip_filename = f"clip_{index}.mp4"

        clip_path = (
            video_clips_dir /
            clip_filename
        )

        command = [
            "ffmpeg",
            "-y",

            "-ss",
            str(start),

            "-i",
            video_path,

            "-t",
            str(duration),

            "-c:v",
            "libx264",

            "-c:a",
            "aac",

            str(clip_path),
        ]

        subprocess.run(
            command,
            check=True,
        )

        clips.append({
            "clip_id": f"clip_{index}",
            "start": start,
            "end": end,
            "duration": duration,
            "reason": highlight["reason"],
            "video_url": (
                f"/clips/{video_id}/{clip_filename}"
            ),
        })

    return clips