from google import genai
from google.genai import types
import json

from app.config import GEMINI_API_KEY


client = genai.Client(
    api_key=GEMINI_API_KEY
)

def transcribe_audio(audio_path: str):

    audio_file = client.files.upload(
        file=audio_path
    )

    prompt = prompt = """
    Transcribe the entire audio file.

    Create a segment whenever there is a natural change in speech.

    For every segment:
    - start = timestamp in seconds
    - end = timestamp in seconds
    - text = exact spoken words

    Do not summarize.
    Do not skip spoken words.
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            prompt,
            audio_file
        ],
        config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {
                                "type": "number"
                            },
                            "end": {
                                "type": "number"
                            },
                            "text": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "start",
                            "end",
                            "text"
                        ]
                    }
                }
            },
            "required": [
                "segments"
            ]
        }
    )
    )

    transcript = json.loads(response.text)

    return transcript
