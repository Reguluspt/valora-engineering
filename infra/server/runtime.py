"""Deployment-only config/secrets and dependency checks; never runs migrations or providers."""
import os
from pathlib import Path, PurePosixPath
import re
import socket
import sys
from urllib.parse import urlsplit
from urllib.request import urlopen

SECRETS = {
    "postgres_password": "POSTGRES_PASSWORD",
    "app_secret_key": "APP_SECRET_KEY",
    "s3_access_key": "S3_ACCESS_KEY_ID",
    "s3_secret_key": "S3_SECRET_ACCESS_KEY",
}


def load_secrets(root=Path("/run/secrets")):
    for name, variable in SECRETS.items():
        try:
            value = (root / name).read_text(encoding="utf-8").strip()
        except OSError:
            raise ValueError("required secret file unavailable") from None
        if len(value) < (16 if name == "s3_access_key" else 32) or "\n" in value:
            raise ValueError("invalid secret file")
        if name == "postgres_password" and not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("database secret must be URL-safe for existing Settings contract")
        os.environ[variable] = value


def check_config():
    origin = urlsplit(os.environ.get("BACKEND_CORS_ORIGINS", ""))
    if (
        os.environ.get("VALORA_ENV") != "production"
        or origin.scheme != "https" or not origin.hostname
        or origin.username or origin.password or origin.path or origin.query or origin.fragment
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", origin.hostname)
        or "," in origin.netloc or origin.port not in (None, 443)
        or os.environ.get("DOCUMENT_BLOB_PROVIDER") != "local"
        or not PurePosixPath(os.environ.get("DOCUMENT_BLOB_ROOT", "")).is_absolute()
        or not re.fullmatch(r"[a-z0-9]+", os.environ.get("VALORA_SCHEMA_HEAD", ""))
    ):
        raise ValueError("invalid server configuration")


def check_dependencies():
    from app.core.config import get_settings
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool
    from app.modules.document_workspace.infrastructure.local_filesystem_document_blob_store import (
        LocalFilesystemDocumentBlobStore,
    )
    import boto3
    from botocore.config import Config

    settings = get_settings()
    engine = create_engine(settings.database_url, poolclass=NullPool, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as connection:
            connection.execute(text("SET statement_timeout = 3000"))
            heads = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
            if heads != {os.environ["VALORA_SCHEMA_HEAD"]}:
                raise ValueError("schema mismatch")
    finally:
        engine.dispose()
    LocalFilesystemDocumentBlobStore(root=settings.document_blob_root)
    client = boto3.client(
        "s3", endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id, aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(connect_timeout=3, read_timeout=3, retries={"max_attempts": 0}),
    )
    client.head_bucket(Bucket=settings.s3_bucket)
    cache = urlsplit(settings.redis_url)
    with socket.create_connection((cache.hostname, cache.port or 6379), timeout=3) as connection:
        connection.sendall(b"*1\r\n$4\r\nPING\r\n")
        if connection.recv(64) != b"+PONG\r\n":
            raise ValueError("supporting cache unavailable")


def main():
    try:
        load_secrets()
        check_config()
        check_dependencies()
        if sys.argv[1] == "ready":
            if sys.argv[2] == "backend":
                with urlopen("http://127.0.0.1:8000/health", timeout=3) as response:
                    if response.status != 200:
                        raise ValueError("API unavailable")
            elif b"worker.main" not in Path("/proc/1/cmdline").read_bytes():
                raise ValueError("worker process unavailable")
            print("server dependency readiness: PASS")
            return
        if sys.argv[1] == "backend":
            command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
        elif sys.argv[1] == "worker":
            command = [sys.executable, "-m", "worker.main"]
        else:
            raise ValueError("unknown startup mode")
        os.execv(sys.executable, command)
    except Exception:
        # Dependency exceptions may contain URLs/credentials; never emit exception details.
        print("server startup/readiness: FAIL (check private configuration and dependencies)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
