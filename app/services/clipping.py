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
    generated_paths = []
    num_clips = len(highlights["clips"])

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

        # Audio micro-fade (only apply if clip is long enough)
        audio_filter = None
        if duration > 0.3:
            audio_fade = 0.15
            audio_filter = f"afade=t=in:ss=0:d={audio_fade},afade=t=out:st={duration - audio_fade}:d={audio_fade}"

        # Video fade only at absolute beginning of first clip and end of last clip (only if clip is at least 1s long)
        video_filter = None
        if duration > 1.0:
            video_filters = []
            if index == 1:
                video_filters.append("fade=t=in:st=0:d=0.5")
            if index == num_clips:
                video_filters.append(f"fade=t=out:st={duration - 0.5}:d=0.5")
            video_filter = ",".join(video_filters) if video_filters else None

        command = [
            "ffmpeg",
            "-y",

            "-ss",
            str(start),

            "-i",
            video_path,

            "-t",
            str(duration),
        ]

        if video_filter:
            command.extend([
                "-vf",
                video_filter
            ])

        if audio_filter:
            command.extend([
                "-af",
                audio_filter
            ])

        command.extend([
            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-c:a",
            "aac",

            str(clip_path),
        ])

        subprocess.run(
            command,
            check=True,
        )

        generated_paths.append(clip_path.resolve())

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

    # Merge individual clips into a single compiled file if we have clips
    merged_clip_url = None
    if len(generated_paths) > 1:
        concat_file_path = video_clips_dir / "concat_list.txt"
        
        # Write list of absolute paths formatted for FFmpeg concat demuxer
        with concat_file_path.open("w", encoding="utf-8") as f:
            for path in generated_paths:
                # Replace backslashes with forward slashes for Windows compatibility in FFmpeg files
                safe_path = str(path).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")

        merged_filename = "merged.mp4"
        merged_path = video_clips_dir / merged_filename

        concat_command = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file_path),
            "-c", "copy",
            str(merged_path)
        ]

        try:
            subprocess.run(concat_command, check=True)
            concat_file_path.unlink(missing_ok=True)
            merged_clip_url = f"/clips/{video_id}/{merged_filename}"
        except Exception:
            # Fallback if concat fails
            pass
    elif len(generated_paths) == 1:
        # If there's only one clip, the merged file is just the single clip
        merged_clip_url = clips[0]["clip_url"]

    return {
        "clips": clips,
        "merged_clip_url": merged_clip_url
    }