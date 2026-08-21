from google.genai import types
import json
from app.clients.gemini import client

def find_highlights(audio_path: str, user_prompt: str):
    # Upload the audio file to Gemini
    audio_file = client.files.upload(
        file=audio_path
    )

    prompt = f"""
        You are an expert trailer and video editor. Your task is to select highlight clips that, when compiled, will form an extremely engaging, high-energy teaser.

        User's requirements/context:
        {user_prompt}

        Follow these structural guidelines to make it look and feel like a teaser:
        1. Select 3 to 5 distinct, non-contiguous moments from different parts of the entire audio timeline (spread across beginning, middle, and end). Do NOT select a single long block.
        2. Keep each individual clip short and snappy: between 10 to 25 seconds in duration.
        3. Structure the clips in a clear "teaser narrative arc":
           - Clip 1: Must be a powerful HOOK (an intriguing question, a shocking statement, or a high-energy quote) that grabs attention instantly.
           - Clips 2-4: Must show the core insights, emotional peaks, major revelations, or key actions.
           - Final Clip: Must be a strong resolution, punchy outro, or memorable takeaway that leaves the viewer wanting to see the full video.
        4. Select complete, meaningful statements that make sense as standalone highlights (no trailing or incomplete sentences).
        5. Speech Cutoff Prevention: Ensure start and end timestamps align exactly with natural pauses in speech. The start timestamp must be right before a new sentence begins, and the end timestamp must be right after a sentence is completely finished. NEVER start or end a clip in the middle of a spoken word or incomplete phrase.
        6. Return the exact start and end timestamps (in seconds) of each selected clip.
        7. Return a short summary of the clip in the 'text' property.
    """

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]

    response = None
    last_exc = None

    try:
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        audio_file,
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "clips": {
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
                                "clips"
                            ]
                        }
                    )
                )
                # Break if request succeeds
                break
            except Exception as exc:
                last_exc = exc
                continue

        if response is None:
            raise last_exc

        highlights = json.loads(response.text)
    finally:
        # Delete the file from Gemini storage to keep it clean
        try:
            client.files.delete(name=audio_file.name)
        except Exception:
            pass

    return highlights


