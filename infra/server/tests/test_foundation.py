"""Adversarial release and startup boundary checks; no live credentials or providers."""
import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class FoundationTests(unittest.TestCase):
    def test_release_rejects_floating_images_and_revision_mismatch(self):
        self.assertTrue((ROOT / "validate.py").is_file(), "release validator missing")
        validator = module("validate")
        manifest = validator.proof_manifest()
        validator.check_manifest(manifest)
        for mutation in ("tag", "revision", "ai"):
            invalid = copy.deepcopy(manifest)
            if mutation == "tag":
                invalid["images"]["backend"]["reference"] = "valora/backend:latest"
            elif mutation == "revision":
                invalid["images"]["frontend"]["revision"] = "b" * 40
            else:
                invalid["images"]["ollama"] = invalid["images"]["backend"]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validator.check_manifest(invalid)

    def test_compose_rejects_database_port_and_external_data_network(self):
        self.assertTrue((ROOT / "validate.py").is_file(), "topology validator missing")
        validator = module("validate")
        config = validator.render_proof()
        validator.check_compose(config)
        for mutation in ("port", "network", "host", "secret"):
            invalid = copy.deepcopy(config)
            if mutation == "port":
                invalid["services"]["postgres"]["ports"] = [{"published": "5432"}]
            elif mutation == "network":
                invalid["networks"]["data"]["internal"] = False
            elif mutation == "host":
                invalid["services"]["backend"]["network_mode"] = "host"
            else:
                invalid["services"]["backend"]["environment"]["POSTGRES_PASSWORD"] = "unsafe"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validator.check_compose(invalid)

    def test_secrets_are_required_and_never_overridden_by_environment(self):
        self.assertTrue((ROOT / "runtime.py").is_file(), "startup secret boundary missing")
        runtime = module("runtime")
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            with self.assertRaises(ValueError):
                runtime.load_secrets(root)
            for name in runtime.SECRETS:
                (root / name).write_text("a" * 48, encoding="utf-8")
            os.environ["POSTGRES_PASSWORD"] = "ambient-value"
            runtime.load_secrets(root)
            self.assertEqual(os.environ["POSTGRES_PASSWORD"], "a" * 48)
            (root / "postgres_password").write_text("contains@url:syntax", encoding="utf-8")
            with self.assertRaises(ValueError):
                runtime.load_secrets(root)

    def test_startup_rejects_http_wildcards_and_schema_omission(self):
        self.assertTrue((ROOT / "runtime.py").is_file(), "startup config boundary missing")
        runtime = module("runtime")
        valid = {
            "VALORA_ENV": "production", "BACKEND_CORS_ORIGINS": "https://valora.example.invalid",
            "DOCUMENT_BLOB_PROVIDER": "local", "DOCUMENT_BLOB_ROOT": "/var/lib/valora/blobs",
            "VALORA_SCHEMA_HEAD": "b5c6d7e8f9a0",
        }
        for value in ("http://valora.example.invalid", "*", "https://host/path", "https://host,https://other"):
            with patch.dict(os.environ, {**valid, "BACKEND_CORS_ORIGINS": value}, clear=True):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    runtime.check_config()
        with patch.dict(os.environ, valid, clear=True):
            runtime.check_config()
            del os.environ["VALORA_SCHEMA_HEAD"]
            with self.assertRaises(ValueError):
                runtime.check_config()


if __name__ == "__main__":
    unittest.main()
