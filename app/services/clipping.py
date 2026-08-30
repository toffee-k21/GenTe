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
        start = float(highlight["start"])
        end = float(highlight["end"])

        if start < 0:
            raise ValueError(
                f"Invalid start timestamp: {start}"
            )

        if end <= start:
            raise ValueError(
                f"Invalid highlight range: {start} -> {end}"
            )

        duration = end - start

        if duration < 10 or duration > 25:
            raise ValueError(
                f"Invalid clip duration: {duration:.2f}s"
            )

        clip_filename = f"clip_{index}.mp4"

        clip_path = (
            video_clips_dir / clip_filename
        )

        command = [
            get_ffmpeg_path(),
            "-y",

            "-ss", str(start),
            "-i", video_path,

            "-t", str(duration),

            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-threads", "1",

            "-c:a", "aac",

            str(clip_path),
        ]

        print(
            f"[FFmpeg] Creating clip {index}: "
            f"{start:.2f}s -> {end:.2f}s"
        )

        subprocess.run(
            command,
            check=True,
        )

        clips.append({
            "clip_id": f"clip_{index}",
            "start": start,
            "end": end,
            "duration": duration,
            "reason": highlight["text"],
            "clip_url": (
                f"/clips/{video_id}/{clip_filename}"
            ),
        })

    return clips


def merge_clips(
    video_id: str,
    clips: list[dict],
):
    video_clips_dir = CLIPS_DIR / video_id
    concat_file = video_clips_dir / "concat.txt"
    teaser_path = video_clips_dir / "teaser.mp4"

    concat_file.write_text(
        "\n".join(
            f"file '{(video_clips_dir / Path(clip['clip_url']).name).resolve().as_posix()}'"
            for clip in clips
        ),
        encoding="utf-8",
    )

    command = [
        get_ffmpeg_path(),
        "-y",

        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),

        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-threads", "1",

        "-c:a", "aac",

        "-movflags", "+faststart",

        str(teaser_path),
    ]


    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg merge failed:\n{result.stderr}"
        )

    return f"/clips/{video_id}/teaser.mp4"