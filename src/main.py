from loguru import logger
import runpod
from src.transcribe import transcribe_voice
from shared.s3_module.s3_client import S3Client


# TODO: add protobuf types and error handling for job
def handler(job):
    logger.debug(f"Received job: {job}")
    job_input = job['input']

    s3_client = S3Client(session_id=job_input['session_id'], test_id=job_input['test_id'])

    voice_file = s3_client.download_file(job_input['voice_path'])

    transcription = transcribe_voice(voice_file, job_input['language'], job_input['model_name'])

    return transcription


if __name__ == '__main__':
    runpod.serverless.start({"handler": handler})
