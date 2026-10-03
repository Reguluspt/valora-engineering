"""Disposable loopback-only TLS proxy proof; generated certificates are test fixtures."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import time
import uuid

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "nginx@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236"
HOST = "valora.example.invalid"


def docker(*args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout.strip()


def main():
    name = "valora-srv0-tls-proof-" + uuid.uuid4().hex[:12]
    network = name + "-net"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, HOST)])
        now = datetime.now(timezone.utc)
        cert = x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1)).add_extension(x509.SubjectAlternativeName([x509.DNSName(HOST)]), critical=False).sign(key, hashes.SHA256())
        (root / "tls_certificate").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        (root / "tls_private_key").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        # These loopback upstreams echo only synthetic headers; no application/provider is started.
        config = '''
server { listen 8000; server_name backend;
    add_header Set-Cookie "__Host-Access-Token=fixture; Secure; HttpOnly; Path=/";
    location / { return 200 "$http_host|$http_origin|$http_x_csrf_token|$http_cookie|$http_x_forwarded_proto"; }
}
server { listen 80; server_name frontend; location / { return 200 "static-fixture"; } }
'''
        (root / "proxy.conf").write_text(config, encoding="utf-8")
        try:
            docker("network", "create", network)
            docker("run", "-d", "--name", name, "--network", network, "--add-host", "backend:127.0.0.1", "--add-host", "frontend:127.0.0.1", "-p", "127.0.0.1::443", "-e", f"VALORA_HOSTNAME={HOST}", "-e", "NGINX_ENVSUBST_FILTER=^VALORA_HOSTNAME$", "--mount", f"type=bind,src={ROOT / 'nginx.conf.template'},dst=/etc/nginx/templates/default.conf.template,readonly", "--mount", f"type=bind,src={root / 'proxy.conf'},dst=/etc/nginx/conf.d/proof-upstreams.conf,readonly", "--mount", f"type=bind,src={root},dst=/run/secrets,readonly", IMAGE)
            docker("exec", name, "nginx", "-t")
            rendered = docker("exec", name, "cat", "/etc/nginx/conf.d/default.conf")
            assert "${VALORA_HOSTNAME}" not in rendered
            assert "$http_host" in rendered and "$remote_addr" in rendered
            port_output = docker("port", name, "443/tcp")
            port = int(port_output.rsplit(":", 1)[1])
            trusted = ssl.create_default_context(cafile=str(root / "tls_certificate"))

            def request(context, hostname=HOST):
                with socket.create_connection(("127.0.0.1", port), timeout=3) as raw:
                    with context.wrap_socket(raw, server_hostname=hostname) as tls:
                        tls.sendall(f"GET /api/proof HTTP/1.0\r\nHost: {HOST}\r\nOrigin: https://{HOST}\r\nX-CSRF-Token: fixture-csrf\r\nCookie: fixture-cookie\r\nX-Forwarded-Proto: http\r\n\r\n".encode())
                        chunks = []
                        while chunk := tls.recv(4096):
                            chunks.append(chunk)
                        return b"".join(chunks).decode()

            for attempt in range(20):
                try:
                    response = request(trusted)
                    break
                except (ConnectionError, TimeoutError):
                    if attempt == 19:
                        raise
                    time.sleep(0.2)
            assert "200 OK" in response
            assert f"{HOST}|https://{HOST}|fixture-csrf|fixture-cookie|https" in response
            assert "Secure; HttpOnly; Path=/" in response
            for context, hostname in ((ssl.create_default_context(), HOST), (trusted, "wrong.example.invalid")):
                try:
                    request(context, hostname)
                except ssl.SSLError:
                    continue
                raise AssertionError("invalid trust/hostname was accepted")
            print("SRV-0 TLS/proxy proof: PASS (real envsubst, trusted chain, untrusted/wrong-host rejection, cookie/origin/CSRF preservation)")
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
            subprocess.run(["docker", "network", "rm", network], capture_output=True, check=False)


if __name__ == "__main__":
    main()
