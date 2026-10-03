"""Run against isolated CI PostgreSQL/Redis/S3 services after existing migrations; no providers."""
import importlib.util
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = importlib.util.spec_from_file_location("server_runtime", ROOT / "runtime.py")
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    with tempfile.TemporaryDirectory() as directory:
        os.chmod(directory, 0o700)
        os.environ.update({
            "VALORA_ENV": "production", "BACKEND_CORS_ORIGINS": "https://valora.example.invalid",
            "DOCUMENT_BLOB_PROVIDER": "local", "DOCUMENT_BLOB_ROOT": directory,
        })
        validate_spec = importlib.util.spec_from_file_location("server_validate", ROOT / "validate.py")
        validate = importlib.util.module_from_spec(validate_spec)
        validate_spec.loader.exec_module(validate)
        os.environ["VALORA_SCHEMA_HEAD"] = validate.schema_head()
        runtime.check_config()
        runtime.check_dependencies()
        os.environ["VALORA_SCHEMA_HEAD"] = "incorrect"
        try:
            runtime.check_dependencies()
        except ValueError:
            pass
        else:
            raise AssertionError("schema mismatch was accepted")
    print("SRV-0 dependency proof: PASS (real DB/schema, POSIX immutable blob probe, bucket, Redis; schema mismatch rejected; no AI/providers)")


if __name__ == "__main__":
    main()
