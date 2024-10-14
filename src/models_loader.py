from loguru import logger
import whisper_timestamped
from device import device
from shared.config.settings import Settings


def initialize_whisper_timestamped_model(name: str):
    model = whisper_timestamped.load_model(name, device=device, in_memory=True)
    logger.debug(f'Whisper Timestamped model is initialized')

    return model


if __name__ == '__main__':
    # TODO: Think about multiprocessing here
    for name in [model_name for model_name in Settings.WhisperModels]:
        initialize_whisper_timestamped_model(name.name)
