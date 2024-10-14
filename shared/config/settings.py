import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class Environment(Enum):
    LOCAL = "local"
    DEV = "dev"
    RUNPOD = "runpod"


class Settings:
    APP_PORT = int(os.getenv('APP_PORT', 4000))

    # Environment
    ENV: Environment = os.getenv("ENV", "local")

    # S3
    S3_HOST: str = os.getenv("S3_HOST")
    S3_PORT: int = int(os.getenv("S3_PORT", 443))
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY")
    S3_UPLOAD_ANALYSIS_BUCKET: str = os.getenv("S3_UPLOAD_ANALYSIS_BUCKET")
    S3_VERSION: str = os.getenv("S3_VERSION", "v0.0.1")

    class WhisperModels(Enum):
        MEDIUM = "medium"
        LARGE = "large"
        LARGE_V2 = "large-v2"
        LARGE_V3 = "large-v3"

    FEATURE_FLAGS: dict = {
        "FF_DEBUG_MOCK_S3": os.getenv("FF_DEBUG_MOCK_S3", "false"),
        "FF_DEBUG_UPLOAD_ANALYSIS_FILE": os.getenv("FF_DEBUG_UPLOAD_ANALYSIS_FILE", "false"),
    }

    @classmethod
    def is_runpod(cls) -> bool:
        return Environment(cls.ENV) == Environment.RUNPOD

    @classmethod
    def has_feature_flag(cls, flag: str) -> bool:
        return cls.FEATURE_FLAGS.get(flag, "false").lower() == "true"
