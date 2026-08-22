from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp


ALLOWED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
}

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
CHUNK_SIZE = 1024 * 1024  # 1 MB


def validate_url(url: str) -> None:
    """Validate that the supplied value is an HTTP/HTTPS URL."""
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.netloc:
        raise ValueError("Invalid video URL.")


def _download_direct_video(url: str, output_path: Path) -> bool:
    """
    Try to download a URL directly.

    Returns True if the URL appears to point directly to a video.
    Returns False when the URL isn't a direct video resource.
    """

    try:
        with requests.get(
            url,
            stream=True,
            timeout=(10, 60),
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        ) as response:

            response.raise_for_status()

            content_type = (
                response.headers.get("content-type", "")
                .lower()
                .split(";")[0]
            )

            # Only treat the response as a direct video if the
            # server explicitly tells us it is a video.
            if not content_type.startswith("video/"):
                return False

            content_length = response.headers.get("content-length")

            if content_length:
                if int(content_length) > MAX_FILE_SIZE:
                    raise ValueError(
                        "Video exceeds the maximum allowed size of 2 GB."
                    )

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            downloaded = 0

            with output_path.open("wb") as output_file:
                for chunk in response.iter_content(
                    chunk_size=CHUNK_SIZE
                ):
                    if not chunk:
                        continue

                    downloaded += len(chunk)

                    if downloaded > MAX_FILE_SIZE:
                        output_file.close()

                        if output_path.exists():
                            output_path.unlink()

                        raise ValueError(
                            "Video exceeds the maximum allowed size of 2 GB."
                        )

                    output_file.write(chunk)

            return True

    except requests.RequestException:
        return False


def _download_with_ytdlp(url: str, output_path: Path) -> None:
    """
    Download a video using yt-dlp.

    This supports platform URLs such as YouTube and other
    websites supported by yt-dlp.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # yt-dlp uses an output template.
    # We use the requested output path directly.
    output_template = str(
        output_path.with_suffix("")
    ) + ".%(ext)s"

    options = {
        "outtmpl": output_template,

        # Prefer a video format that has both video and audio.
        # Fall back to separate video/audio streams if necessary.
        "format": (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "best[ext=mp4]/"
            "best"
        ),

        "merge_output_format": "mp4",

        "noplaylist": True,

        "quiet": True,

        "no_warnings": True,

        "max_filesize": MAX_FILE_SIZE,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

    except Exception as exc:
        raise RuntimeError(
            f"Unable to download video from URL: {exc}"
        ) from exc

    # yt-dlp may produce .mp4 after merging.
    generated_mp4 = output_path.with_suffix(".mp4")

    if generated_mp4.exists():
        if generated_mp4 != output_path:
            generated_mp4.replace(output_path)

        return

    # Sometimes yt-dlp may use another extension.
    possible_files = list(
        output_path.parent.glob(
            f"{output_path.stem}.*"
        )
    )

    possible_files = [
        path
        for path in possible_files
        if path.suffix.lower() in ALLOWED_EXTENSIONS
    ]

    if not possible_files:
        raise RuntimeError(
            "Video download completed, but no video file was produced."
        )

    possible_files[0].replace(output_path)


def download_video(url: str, output_path: str) -> str:
    """
    Download a video from either:

    1. A direct video URL
    2. A supported platform URL

    Returns the local video path.
    """

    validate_url(url)

    output = Path(output_path)

    # First try a normal/direct video download.
    direct_downloaded = _download_direct_video(
        url,
        output,
    )

    if direct_downloaded:
        return str(output)

    # If it isn't a direct video URL, use yt-dlp.
    _download_with_ytdlp(
        url,
        output,
    )

    if not output.exists():
        raise RuntimeError(
            "Video could not be downloaded."
        )

    return str(output)