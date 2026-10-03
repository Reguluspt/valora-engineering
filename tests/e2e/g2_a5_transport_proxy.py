"""Local acceptance transport: real API forwarding plus one lost committed response.

Never mocks business results. Fault flag is consumed only after upstream success.
No cookies, passwords, tokens, values or reason notes are logged.
"""
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

TARGET = "http://127.0.0.1:8001"
EVIDENCE = Path(os.environ["A5_EVIDENCE_DIR"]).resolve()
FAULT = EVIDENCE / "drop-next-validation-response.flag"
HOP = {"connection", "transfer-encoding", "content-length", "host"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def forward(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        response = httpx.request(self.command, TARGET + self.path, content=raw,
                                 headers={k: v for k, v in self.headers.items() if k.lower() not in HOP},
                                 timeout=60)
        payload = json.loads(raw) if raw and "application/json" in self.headers.get("Content-Type", "") else {}
        lost = self.command == "POST" and self.path.endswith("/validate") and response.status_code == 200 and FAULT.exists()
        record = {"method": self.command, "path": self.path, "status": response.status_code,
                  "response_dropped": lost, "command_id": payload.get("command_id"),
                  "contract_version": payload.get("contract_version")}
        with (EVIDENCE / "transport.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record) + "\n")
        if lost:
            FAULT.unlink()
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        self.send_response(response.status_code)
        for key, value in response.headers.multi_items():
            if key.lower() not in HOP and key.lower() != "content-encoding":
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(response.content)))
        self.end_headers()
        self.wfile.write(response.content)

    do_GET = forward
    do_POST = forward
    do_PUT = forward
    do_PATCH = forward
    do_DELETE = forward

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
