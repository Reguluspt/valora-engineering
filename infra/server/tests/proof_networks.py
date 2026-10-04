"""Disposable real bridge/route proof of rendered topology; no Internet/provider calls."""
import importlib.util
import json
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
# Same disposable Linux fixture as TLS proof, never an application or S3 runtime image.
IMAGE = "nginx@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236"


def docker(*args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout.strip()


def main():
    spec = importlib.util.spec_from_file_location("server_validate", ROOT / "validate.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    config = validator.render_proof()
    prefix = "valora-srv0-network-proof-" + uuid.uuid4().hex[:12]
    networks, containers = [], []
    try:
        for name, network in config["networks"].items():
            actual = prefix + "-" + name
            docker("network", "create", "--driver", "bridge", *(["--internal"] if network.get("internal") else []), actual)
            networks.append(actual)
            inspected = json.loads(docker("network", "inspect", actual))[0]
            assert inspected["Internal"] == (name in {"app", "data"})
        for name, service in config["services"].items():
            actual = prefix + "-" + name
            attached = list(service["networks"])
            docker("create", "--name", actual, "--network", prefix + "-" + attached[0], "--entrypoint", "/bin/sh", IMAGE, "-c", "sleep 120")
            containers.append(actual)
            for network in attached[1:]:
                docker("network", "connect", prefix + "-" + network, actual)
            docker("start", actual)
            inspected = json.loads(docker("inspect", actual))[0]
            assert not inspected["HostConfig"]["PortBindings"]
            assert set(inspected["NetworkSettings"]["Networks"]) == {prefix + "-" + network for network in attached}
            routes = docker("exec", actual, "cat", "/proc/net/route").splitlines()[1:]
            default_routes = [row.split() for row in routes if row.split()[1] == "00000000"]
            assert bool(default_routes) == (name in {"ingress", "backend", "worker"}), (name, routes)
            if name in {"backend", "worker"}:
                gateway = inspected["NetworkSettings"]["Networks"][prefix + "-egress"]["Gateway"]
                assert gateway
                gateway_hex = "".join(f"{int(part):02X}" for part in reversed(gateway.split(".")))
                assert any(row[2] == gateway_hex for row in default_routes), (name, routes)
        print("SRV-0 network proof: PASS (rendered attachments, real default routes through dedicated egress, internal data/frontend isolation; fixtures publish no ports; no provider calls)")
    finally:
        for name in reversed(containers):
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
        for name in reversed(networks):
            subprocess.run(["docker", "network", "rm", name], capture_output=True, check=False)


if __name__ == "__main__":
    main()
