from openai import OpenAI

from app.config import OPENAI_API_KEY


client = OpenAI(
    api_key=OPENAI_API_KEY
)


def transcribe_audio(
    audio_path: str
):

    with open(
        audio_path,
        "rb"
    ) as audio_file:

        response = (
            client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=[
                    "segment"
                ],
            )
        )

    return response

#note : here audio_file is a file **object**, that is created by py to let users interact with the file. like read, write etc....it is not the actual data , or binary of audio file