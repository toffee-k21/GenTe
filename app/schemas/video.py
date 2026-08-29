# app/schemas/video.py

from typing import Literal

from pydantic import BaseModel


class VideoVisibilitySchema(BaseModel):

    visibility: Literal[
        "public",
        "private"
    ]