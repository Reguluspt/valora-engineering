"""Real API forwarding with one lost committed supplier-quotation response."""
import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import httpx

EVIDENCE = Path(os.environ["A14_EVIDENCE_DIR"])
FAULT = EVIDENCE / "drop-next-quote-response.flag"
HOP = {"connection", "transfer-encoding", "content-length", "host", "content-encoding"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def forward(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        response = httpx.request(self.command, "http://127.0.0.1:8001" + self.path, content=raw,
            headers={k: v for k, v in self.headers.items() if k.lower() not in HOP}, timeout=60)
        payload = json.loads(raw) if raw and "application/json" in self.headers.get("Content-Type", "") else {}
        lost = self.command == "POST" and "/supplier-quotes/" in self.path and response.status_code == 200 and FAULT.exists()
        if "/supplier-quotes" in self.path:
            with (EVIDENCE / "transport.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"method": self.command, "path": self.path, "status": response.status_code,
                    "response_dropped": lost, "command_id": payload.get("command_id"), "contract_version": payload.get("contract_version")}) + "\n")
        if lost:
            FAULT.unlink()
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        self.send_response(response.status_code)
        for key, value in response.headers.multi_items():
            if key.lower() not in HOP:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(response.content)))
        self.end_headers()
        self.wfile.write(response.content)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = forward

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
