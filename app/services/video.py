import subprocess


def extract_audio(
    video_path: str,
    audio_path: str
) -> None:

    command = [
        "ffmpeg",

        "-y",

        "-i",
        video_path,

        "-vn",

        "-acodec",
        "mp3",

        "-ar",
        "16000",

        "-ac",
        "1",

        audio_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed:\n{result.stderr}"
        )

    