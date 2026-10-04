"""Historical 2026-10-03 dev compatibility only; never SRV-0 slot or vendor certification."""
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from urllib.error import URLError
from urllib.request import urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Existing dev vendor RELEASE.2024-12-18T13-15-44Z; confirmed by this digest's --version.
IMAGE = "minio/minio@sha256:1dce27c494a16bae114774f1cec295493f3613142713130c2d22dd5696be6ad3"


def docker(*args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout.strip()


def main():
    name = "valora-srv0-minio-proof-" + uuid.uuid4().hex[:12]
    access_id = "srv0_test_only_access_id"
    secret_value = "srv0_test_only_minio_fixture_" + "a" * 32
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "s3_access_key").write_text(access_id, encoding="utf-8")
        (root / "s3_secret_key").write_text(secret_value, encoding="utf-8")
        try:
            docker("run", "-d", "--name", name, "-p", "127.0.0.1::9000", "-e", "MINIO_ROOT_USER_FILE=/run/secrets/s3_access_key", "-e", "MINIO_ROOT_PASSWORD_FILE=/run/secrets/s3_secret_key", "--mount", f"type=bind,src={root},dst=/run/secrets,readonly", IMAGE, "server", "/data")
            port = int(docker("port", name, "9000/tcp").rsplit(":", 1)[1])
            for attempt in range(40):
                try:
                    with urlopen(f"http://127.0.0.1:{port}/minio/health/ready", timeout=1) as response:
                        assert response.status == 200
                    break
                except (URLError, ConnectionError, TimeoutError):
                    if attempt == 39:
                        raise
                    time.sleep(0.2)
            options = {"endpoint_url": f"http://127.0.0.1:{port}", "region_name": "us-east-1", "config": Config(signature_version="s3v4", connect_timeout=1, read_timeout=1, retries={"max_attempts": 0})}
            client = boto3.client("s3", aws_access_key_id=access_id, aws_secret_access_key=secret_value, **options)
            client.create_bucket(Bucket="srv0-file-secret-proof")
            client.head_bucket(Bucket="srv0-file-secret-proof")
            default = boto3.client("s3", aws_access_key_id="minioadmin", aws_secret_access_key="minioadmin", **options)
            try:
                default.head_bucket(Bucket="srv0-file-secret-proof")
            except ClientError as error:
                assert error.response["ResponseMetadata"]["HTTPStatusCode"] == 403
            else:
                raise AssertionError("default MinIO credentials were accepted")
            print("Historical MinIO compatibility: PASS (dated dev fixture only; no production runtime/slot certification)")
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


if __name__ == "__main__":
    main()
