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
    Transcribe the entire audio.

    Return ONLY valid JSON in this exact format:

    {
        "segments": [
            {
                "start": 0.0,
                "end": 5.2,
                "text": "..."
            }
        ]
    }

    Rules:
    - start and end must be numbers representing seconds
    - text must contain the exact spoken words
    - create a segment whenever there is a natural change in speech
    - do not summarize
    - do not add explanations outside the JSON
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
    print(transcript)

    return transcript

#note : here audio_file is a file **object**, that is created by py to let users interact with the file. like read, write etc....it is not the actual data , or binary of audio file