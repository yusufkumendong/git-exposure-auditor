#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SPA = b"<!doctype html><html><head><title>Example App</title></head><body>Application shell</body></html>"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/.git/HEAD":
            self.reply(200, b"ref: refs/heads/main\n", "text/plain")
        elif self.path == "/.git/config":
            self.reply(200, SPA, "text/html")
        elif self.path == "/.git/packed-refs":
            self.reply(503, b"temporary upstream error\n", "text/plain", {"Retry-After": "0"})
        elif self.path == "/.git/refs/heads/main":
            self.reply(200, b"0123456789abcdef0123456789abcdef01234567\n", "text/plain")
        elif self.path == "/.git/refs/heads/master":
            self.reply(404, b"not found\n", "text/plain")
        elif self.path == "/.git/logs/HEAD":
            self.reply(403, b"Checking your browser before accessing this site. Ray ID: test\n", "text/html", {"Server": "cloudflare", "CF-Ray": "test"})
        elif self.path == "/.git/index":
            self.reply(200, b"DIRC\x00\x00\x00\x02", "application/octet-stream")
        elif self.path == "/.git/objects/info/packs":
            self.reply(429, b"rate limited\n", "text/plain", {"Retry-After": "0"})
        elif self.path == "/redirect-out":
            self.reply(302, b"", "text/plain", {"Location": "https://outside.invalid/.git/HEAD"})
        else:
            self.reply(200, SPA, "text/html")

    def reply(self, status, body, content_type, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 18765), Handler).serve_forever()
