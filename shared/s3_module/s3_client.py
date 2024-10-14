import boto3
from botocore.exceptions import ClientError
from loguru import logger
from tempfile import NamedTemporaryFile
from shared.config.settings import Settings
from typing import Dict, Any
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
import os
import json

class S3Client:
    _host: str = Settings.S3_HOST
    _port: int = Settings.S3_PORT
    _access_key: str = Settings.S3_ACCESS_KEY
    _secret_key: str = Settings.S3_SECRET_KEY
    _version: str = Settings.S3_VERSION
    _upload_analysis_bucket: str = Settings.S3_UPLOAD_ANALYSIS_BUCKET

    def __init__(self, is_secure=True, session_id='', test_id=''):
        self._file_path_prefix = os.path.join(self._version, test_id, session_id)

        if Settings.has_feature_flag('FF_DEBUG_MOCK_S3'):
            logger.info('FF_DEBUG_MOCK_S3 set. No connection needed.')
            self.client = None
            return

        logger.info(f"Connecting to S3 at {self._host}:{self._port}")
        endpoint_url = f"{'https' if is_secure else 'http'}://{self._host}:{self._port}"
        self.client = boto3.client(
            's3',
            endpoint_url = endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            use_ssl=is_secure,
        )

    def download_file(self, file_path):
        if Settings.has_feature_flag('FF_DEBUG_MOCK_S3'):
            logger.info(f'FF_DEBUG_MOCK_S3 set. Using local file {file_path}')
            return file_path

        logger.info(f"Downloading file from {file_path}")
        bucket_name, object_name = file_path.split('/', 1)
        _, file_extension = os.path.splitext(file_path)

        try:
            with NamedTemporaryFile(delete=False,suffix=file_extension) as temp_file:
                self.client.download_file(bucket_name, object_name, temp_file.name)
            return temp_file.name
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                logger.error(
                    f"Access denied when trying to download file: {file_path}. Ensure the correct permissions are set.")
            elif e.response['Error']['Code'] == 'NoSuchKey':
                logger.error(f"File not found on bucket: {file_path}")
            else:
                logger.error(f"Error occurred while downloading file {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error occurred while downloading file {file_path}")
            raise

    def download_files(self, files):
        if Settings.has_feature_flag('FF_DEBUG_MOCK_S3'):
            logger.info(f'FF_DEBUG_MOCK_S3 set. Leaving file at {files}')
            return files

        with ThreadPoolExecutor(max_workers=30) as executor:
            future_to_files = { executor.submit(self.download_file, file): file for file in files }

            for future in futures.as_completed(future_to_files):
                file = future_to_files[future]
                exception = future.exception()

                if not exception:
                    yield file, future.result()
                else:
                    yield file, exception

    def _upload_file(self, file_path, object_name, bucket_name):
        if Settings.has_feature_flag('FF_DEBUG_MOCK_S3'):
            logger.info(f'FF_DEBUG_MOCK_S3 set. Leaving file at {file_path}')
            return file_path

        full_object_name = os.path.join(self._file_path_prefix, object_name)
        logger.info(f"Uploading file to {bucket_name}/{full_object_name}")

        try:
            self.client.upload_file(file_path, bucket_name, full_object_name)
            return os.path.join(bucket_name, full_object_name)
        except ClientError as e:
            logger.error(f"Error occurred while uploading file {file_path} to {bucket_name}/{full_object_name}")
            raise

    def upload_analysis_file(self, file_path, object_name):
        return self._upload_file(file_path, object_name, self._upload_analysis_bucket)

    def _check_file_exists(self, file_name, bucket_name: str) -> str | None:
        """
        Check if a file exists in the S3 bucket.
        """
        object_name = f'{self._file_path_prefix}/{file_name}'
        full_path = f'{bucket_name}/{object_name}'
        logger.info(f'full_path {full_path}')
        try:
            self.client.head_object(Bucket=bucket_name, Key=object_name)
            return full_path
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            else:
                raise

    def check_analysis_file_exists(self, result_file_name) -> str | None:
        """
        Check if a result file exists in the S3 bucket WITH FEATURE FLAG ONLY!!
        """
        if Settings.has_feature_flag("FF_DISABLE_CHECKING_OF_EXISTING_RESULT_FILE"):
            return None

        return self._check_file_exists(result_file_name, self._upload_analysis_bucket)

    def dump_json_and_upload(self, object_name: str, data: Dict[str, Any]) -> str:
        with NamedTemporaryFile(delete=not Settings.has_feature_flag('FF_DEBUG_MOCK_S3'), suffix='.json', mode='w') as data_file:
            json.dump(data, data_file, indent=4)
            data_file.flush()  # Ensure all data is written to the file
            path = self.upload_analysis_file(data_file.name, object_name)
            return path

    def list_files_in_bucket(self, bucket_name: str, prefix: str = "") -> list[str]:
        """
        List all file paths in the given S3 bucket under a specific prefix.
        :param bucket_name: The name of the S3 bucket.
        :param prefix: The prefix to filter the objects (optional).
        :return: A list of file paths in the bucket.
        """
        if Settings.has_feature_flag('FF_DEBUG_MOCK_S3'):
            logger.info(f'FF_DEBUG_MOCK_S3 set. No actual listing from bucket {bucket_name}')
            return []

        try:
            logger.info(f"Listing files in bucket: {bucket_name} with prefix: {prefix}")
            response = self.client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

            if 'Contents' not in response:
                logger.info(f"No files found in bucket {bucket_name} with prefix {prefix}")
                return []

            file_paths = [os.path.join(bucket_name, item['Key']) for item in response['Contents']]
            return file_paths
        except ClientError as e:
            logger.error(f"Error occurred while listing files in bucket {bucket_name}")
            raise

    def download_files_from_specific_folder(self, bucket_name, folder_name, local_dir):
        logger.info(f"Listing files in {folder_name} from bucket {bucket_name}")

        files = self.list_files_in_bucket(bucket_name=bucket_name, prefix=folder_name)

        if not files:
            logger.info(f"No files found in folder {folder_name} in bucket {bucket_name}.")
            return

        logger.info(f"Downloading {len(files)} files from folder {folder_name} in bucket {bucket_name}")
        for file, result in self.download_files(files):
            if isinstance(result, Exception):
                logger.error(f"Failed to download {file}: {str(result)}")
            else:
                # Save with proper file name in the ./data directory
                local_file_path = os.path.join(local_dir, os.path.basename(file))
                os.rename(result, local_file_path)
                logger.info(f"Downloaded {file} to {local_file_path}")
