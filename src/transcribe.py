from typing import Dict, Any
from loguru import logger
import re
import json
import whisper_timestamped
from shared.config.settings import Settings
from device import device


def transcribe_voice(voice_file: str, lang: str,
                     model_name: Settings.WhisperModels = Settings.WhisperModels.LARGE_V2) -> Dict[str, Any]:
    audio = whisper_timestamped.load_audio(voice_file)
    model = whisper_timestamped.load_model(model_name.name, device=device)
    wt_result = whisper_timestamped.transcribe(model, audio, vad="auditok", beam_size=5, best_of=5, temperature=1,
                                               language=lang if lang else None)

    logger.debug(
        f'Voice file is transcribed with Whisper Timestamped:\n{json.dumps(wt_result, indent=2, ensure_ascii=False)}')

    result = {
        "language": wt_result["language"],
        "language_probability": 1,
        "segments": []
    }

    for i, segment in enumerate(wt_result["segments"]):
        segment_dict = {
            "id": i,
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
            "words": [{"text": word["text"], "start": word["start"], "end": word["end"],
                       "probability": word["confidence"]} for
                      word in segment["words"]]
        }
        result["segments"].append(segment_dict)

    result["normalized_text"] = normalize_text(extract_text(result), result["language"])

    logger.debug(f'transcription is formatted to result:\n{result}')

    return result


def normalize_text(text, language):
    logger.info("Normalizing text...")
    if language == 'ar':
        text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
        text = re.sub(r'[ﺇﺃﺁﺍ]', 'ﺍ', text)
        text = re.sub(r'[ﻱﻯ]', 'ﻱ', text)
        text = re.sub(r'ﺓ', 'ﻩ', text)
    elif language == 'ru':
        text = text.lower()
        text = re.sub(r'[^а-яё0-9\s]', '', text)
    else:
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
    logger.info(f"Normalized text: {text.strip()}")
    return text.strip()


def extract_text(trans):
    return ' '.join([segment['text'] for segment in trans['segments']])
