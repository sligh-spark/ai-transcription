from loguru import logger
import torch


def get_current_device():
    cuda_available = torch.cuda.is_available()

    if cuda_available:
        logger.info('CUDA is available')
    else:
        logger.warning('CUDA is not available')

    return "cuda" if cuda_available else "cpu"


device = get_current_device()
logger.info(f'The current device is: {device}')
