"""Validate release inputs and normalized Compose without starting or installing services."""
import argparse
import ast
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SERVICES = {"ingress", "frontend", "backend", "worker", "postgres", "redis", "minio"}
APP_IMAGES = {"backend", "worker", "frontend"}
ARTIFACTS = ("compose.yml", "nginx.conf.template", "frontend.conf", "runtime.py")
SECRET_VARIABLES = {"POSTGRES_PASSWORD", "APP_SECRET_KEY", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"}


def schema_head():
    revisions, parents = set(), set()
    for path in (REPO / "backend/alembic/versions").glob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
            for target in targets:
                if isinstance(target, ast.Name) and target.id in ("revision", "down_revision"):
                    value = ast.literal_eval(node.value)
                    if target.id == "revision":
                        revisions.add(value)
                    elif isinstance(value, str):
                        parents.add(value)
                    elif value:
                        parents.update(value)
    heads = revisions - parents
    if len(heads) != 1:
        raise ValueError("release requires exactly one existing Alembic head")
    return heads.pop()


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ARTIFACTS}


def check_manifest(manifest):
    if type(manifest.get("manifest_version")) is not int or manifest["manifest_version"] != 1 or not re.fullmatch(r"[A-Za-z0-9._-]+", manifest.get("release_id") or ""):
        raise ValueError("release identity/version required")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("server_revision") or ""):
        raise ValueError("exact server revision required")
    if manifest.get("web_revision") != manifest["server_revision"]:
        raise ValueError("SRV-0 packages server and web from the same revision")
    if manifest.get("schema_head") != schema_head() or manifest.get("foundation_sha256") != hashes():
        raise ValueError("release schema/foundation artifacts do not match this checkout")
    images = manifest.get("images", {})
    if set(images) != SERVICES:
        raise ValueError("only the approved service/image set is allowed")
    for name, image in images.items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*@sha256:[0-9a-f]{64}", image.get("reference") or ""):
            raise ValueError("immutable image reference required")
        if name in APP_IMAGES and image.get("revision") != manifest["server_revision"]:
            raise ValueError("application image revision mismatch")


def proof_manifest():
    manifest = json.loads((ROOT / "release.example.json").read_text(encoding="utf-8"))
    manifest.update(release_id="shape-proof-only", server_revision="a" * 40, web_revision="a" * 40, schema_head=schema_head(), foundation_sha256=hashes())
    for name, image in manifest["images"].items():
        # Synthetic references are only for config rendering; never pulled or certified as images.
        image["reference"] = f"example.invalid/shape/{name}@sha256:" + "a" * 64
        if name in APP_IMAGES:
            image["revision"] = manifest["server_revision"]
    return manifest


def render(manifest, inputs):
    check_manifest(manifest)
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", inputs.get("VALORA_HOSTNAME", "")):
        raise ValueError("one approved hostname required; no port, path or wildcard")
    address = ipaddress.IPv4Address(inputs.get("VALORA_LAN_IP", ""))
    if address.is_unspecified or address.is_multicast or address.is_loopback or not address.is_private:
        raise ValueError("explicit private LAN IPv4 interface required")
    for key in ("VALORA_SECRET_DIR", "VALORA_BLOB_ROOT"):
        value = inputs.get(key, "")
        if not value.startswith("/") or any(character in value for character in "\n\r$"):
            raise ValueError("absolute external Linux paths required")
        candidate = Path(value).resolve()
        if candidate == REPO or REPO in candidate.parents:
            raise ValueError("runtime data/secrets must be outside the checkout")
    values = {**inputs, "VALORA_SCHEMA_HEAD": manifest["schema_head"]}
    values.update({f"VALORA_{name.upper()}_IMAGE": image["reference"] for name, image in manifest["images"].items()})
    with tempfile.TemporaryDirectory() as directory:
        env_path = Path(directory) / "release.env"
        env_path.write_text("".join(f"{key}={value}\n" for key, value in sorted(values.items())), encoding="utf-8")
        # Ignore ambient VALORA_* overrides so the reviewed manifest owns the rendered image set.
        environment = {key: value for key, value in os.environ.items() if not key.startswith("VALORA_")}
        result = subprocess.run(["docker", "compose", "--env-file", str(env_path), "-f", str(ROOT / "compose.yml"), "config", "--format", "json"], env=environment, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Compose config rejected release inputs")
    config = json.loads(result.stdout)
    check_compose(config)
    for name in SERVICES:
        if config["services"][name]["image"] != manifest["images"][name]["reference"]:
            raise ValueError("Compose image differs from release manifest")
    return config, values


def render_proof():
    return render(proof_manifest(), {
        "VALORA_HOSTNAME": "valora.example.invalid", "VALORA_LAN_IP": "192.168.254.254",
        "VALORA_SECRET_DIR": "/srv/shape-proof/secrets", "VALORA_BLOB_ROOT": "/srv/shape-proof/blobs",
    })[0]


def check_compose(config):
    services, networks = config.get("services", {}), config.get("networks", {})
    if set(services) != SERVICES or set(networks) != {"edge", "app", "data"}:
        raise ValueError("unexpected services or networks")
    if any(not networks[name].get("internal") or networks[name].get("external") for name in ("app", "data")):
        raise ValueError("application and data networks must be private")
    topology = {"ingress": {"edge", "app"}, "frontend": {"app"}, "backend": {"app", "data"}, "worker": {"data"}, "postgres": {"data"}, "redis": {"data"}, "minio": {"data"}}
    for name, service in services.items():
        if set(service.get("networks", {})) != topology[name]:
            raise ValueError("service network boundary changed")
        if any(service.get(key) for key in ("build", "network_mode", "privileged", "devices", "gpus", "external_links")):
            raise ValueError("unapproved service privileges/build/runtime")
        if SECRET_VARIABLES.intersection(service.get("environment", {})):
            raise ValueError("secret values may not appear in Compose environment")
        ports = service.get("ports", [])
        if name != "ingress" and ports:
            raise ValueError("only ingress may publish a port")
        if name == "ingress":
            if len(ports) != 1 or ports[0].get("target") != 443 or str(ports[0].get("published")) != "443":
                raise ValueError("only HTTPS 443 may be exposed")
            address = ipaddress.ip_address(ports[0].get("host_ip", "0.0.0.0"))
            if address.is_unspecified or not address.is_private:
                raise ValueError("ingress must bind the approved private interface")
    for name in ("backend", "worker"):
        service = services[name]
        if service.get("user") != "10001:10001" or not service.get("read_only"):
            raise ValueError("application isolation changed")
        if service["environment"].get("VALORA_ENV") != "production" or service["environment"].get("DOCUMENT_BLOB_PROVIDER") != "local":
            raise ValueError("production immutable-blob authority required")
        if not service.get("healthcheck") or not service.get("secrets"):
            raise ValueError("readiness/secrets contract required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", action="store_true", help="validate non-deployable example shape only")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--env", type=Path, help="non-secret operator input file")
    parser.add_argument("--write-env", type=Path, help="write reviewed Compose inputs outside the checkout")
    args = parser.parse_args()
    try:
        if args.template:
            if args.manifest or args.env or args.write_env:
                raise ValueError("template proof cannot produce installation inputs")
            check_manifest(proof_manifest())
            check_compose(render_proof())
            print("SRV-0 template/Compose shape: PASS (synthetic image references; no install/deploy)")
        else:
            if not args.manifest or not args.env:
                raise ValueError("real manifest and non-secret input file required")
            inputs = {}
            for line in args.env.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    if key not in {"VALORA_HOSTNAME", "VALORA_LAN_IP", "VALORA_SECRET_DIR", "VALORA_BLOB_ROOT"} or key in inputs:
                        raise ValueError("unknown/duplicate operator input")
                    inputs[key] = value
            _, values = render(json.loads(args.manifest.read_text(encoding="utf-8")), inputs)
            if args.write_env:
                destination = args.write_env.resolve()
                if destination == REPO or REPO in destination.parents:
                    raise ValueError("write installation inputs outside the checkout")
                destination.write_text("".join(f"{key}={value}\n" for key, value in sorted(values.items())), encoding="utf-8")
            print("SRV-0 release/Compose contract: PASS (no images pulled; no services started)")
    except (ValueError, OSError, KeyError, TypeError):
        parser.exit(1, "SRV-0 validation: FAIL (invalid release/config contract)\n")


if __name__ == "__main__":
    main()
