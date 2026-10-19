"""Task-only HTTP transport over Docker exec; the Docker network stays internal."""
import base64
import http.client
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LIMIT = 2 * 1024 * 1024


def container_request(message):
    path = message["path"]
    assert path.startswith(("/api/", "/health")) and "\r" not in path and "\n" not in path
    body = base64.b64decode(message["body"], validate=True)
    assert len(body) <= LIMIT
    connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=30)
    connection.request(message["method"], path, body=body or None, headers=message["headers"])
    response = connection.getresponse()
    result = dict(status=response.status, headers=response.getheaders(), body=base64.b64encode(response.read()).decode("ascii"))
    connection.close()
    return result


def host_server():
    root = Path(__file__).resolve().parents[3]
    docker = Path(os.environ["LOCALAPPDATA"]) / "Programs/DockerDesktop/resources/bin/docker.exe"
    transport = subprocess.Popen([str(docker), "compose", "-f", "tests/e2e/issue208/compose.yml", "exec", "-T", "backend",
        "python", "/acceptance/api_bridge.py", "--container-server"], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    transport_lock = threading.Lock()

    class Proxy(BaseHTTPRequestHandler):
        def forward(self):
            if not self.path.startswith(("/api/", "/health")):
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= LIMIT or self.headers.get("Transfer-Encoding"):
                self.send_error(413)
                return
            body = self.rfile.read(length)
            message = dict(method=self.command, path=self.path, body=base64.b64encode(body).decode("ascii"),
                headers={k: v for k, v in self.headers.items() if k.lower() not in {"connection", "content-length", "transfer-encoding"}})
            try:
                with transport_lock:
                    transport.stdin.write(json.dumps(message).encode() + b"\n")
                    transport.stdin.flush()
                    response = json.loads(transport.stdout.readline())
                payload = base64.b64decode(response["body"])
                self.send_response(response["status"])
                for key, value in response["headers"]:
                    if key.lower() not in {"content-length", "transfer-encoding", "connection"}:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (subprocess.SubprocessError, ValueError, OSError):
                self.send_error(502, "Isolated task API transport unavailable")

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = forward

        def log_message(self, *_args):
            pass

    print("Issue 208 task-only API transport listening on loopback:58208", flush=True)
    try:
        ThreadingHTTPServer(("127.0.0.1", 58208), Proxy).serve_forever()
    finally:
        transport.stdin.close()
        transport.wait(timeout=35)


if __name__ == "__main__":
    if "--container-server" in sys.argv:
        for line in sys.stdin.buffer:
            print(json.dumps(container_request(json.loads(line))), flush=True)
    else:
        host_server()
