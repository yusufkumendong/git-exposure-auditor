#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    server_version = "GEATest/2.0"

    def log_message(self, format, *args):
        return

    def send_bytes(self, status: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/.git/HEAD":
            self.send_bytes(200, b"ref: refs/heads/main\n")
            return
        if path == "/.git/config":
            self.send_bytes(200, b"[core]\n\trepositoryformatversion = 0\n\tbare = false\n")
            return
        if path == "/.git/packed-refs":
            self.send_bytes(200, b"# pack-refs with: peeled fully-peeled\n" + b"a" * 40 + b" refs/heads/main\n")
            return
        if path == "/.git/index":
            self.send_bytes(200, b"DIRC" + b"\x00" * 32, "application/octet-stream")
            return
        if path == "/.git/logs/HEAD":
            line = (
                b"0" * 40
                + b" "
                + b"a" * 40
                + b" Test User <test@example.invalid> 1700000000 +0000\tcommit: test\n"
            )
            self.send_bytes(200, line)
            return
        if path.startswith("/soft/"):
            self.send_bytes(200, b"generic application fallback page\n", "text/html")
            return
        if path == "/blocked/.git/HEAD":
            self.send_bytes(403, b"forbidden\n")
            return
        self.send_bytes(404, b"not found\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(args.port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
