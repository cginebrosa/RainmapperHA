from __future__ import annotations

import argparse
import html
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


PLOTS_PATH = Path("/app/Plots")


def html_page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #101418;
      --fg: #e8eef2;
      --muted: #9aa8b2;
      --card: #1b2229;
      --line: #33404a;
      --accent: #03a9f4;
    }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--fg);
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 700;
    }}
    p {{
      color: var(--muted);
      margin: 0 0 20px;
      line-height: 1.45;
    }}
    ul {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 10px;
    }}
    a {{
      display: block;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--fg);
      text-decoration: none;
    }}
    a:focus,
    a:hover {{
      border-color: var(--accent);
    }}
    .meta {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }}
    .empty {{
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
""".encode("utf-8")


def format_size(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class RainmapperHandler(BaseHTTPRequestHandler):
    server_version = "RainmapperMaps/0.1"

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_bytes(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self.render_index()
            return

        if path.startswith("/file/"):
            self.serve_plot(path.removeprefix("/file/"))
            return

        self.send_bytes(
            404,
            html_page("Not found", "<h1>Not found</h1><p>This Rainmapper page does not exist.</p>"),
            "text/html; charset=utf-8",
        )

    def render_index(self) -> None:
        files = sorted(PLOTS_PATH.glob("*.html"))
        if not files:
            listing = (
                '<div class="empty">No HTML maps found in '
                '<code>/share/rainmapper/Plots</code>.</div>'
            )
        else:
            items = []
            for file_path in files:
                stat = file_path.stat()
                name = file_path.name
                title = name.removesuffix(".html").replace("_", " ")
                items.append(
                    "<li>"
                    f'<a href="file/{html.escape(name)}">'
                    f"{html.escape(title)}"
                    f'<span class="meta">{html.escape(name)} - {format_size(stat.st_size)}</span>'
                    "</a>"
                    "</li>"
                )
            listing = "<ul>" + "".join(items) + "</ul>"

        body = (
            "<h1>Rainmapper</h1>"
            "<p>Generated maps from <code>/share/rainmapper/Plots</code>.</p>"
            f"{listing}"
        )
        self.send_bytes(200, html_page("Rainmapper", body), "text/html; charset=utf-8")

    def serve_plot(self, requested_name: str) -> None:
        name = unquote(requested_name)
        if "/" in name or "\\" in name or not name.endswith(".html"):
            self.send_bytes(400, b"Invalid file name", "text/plain; charset=utf-8")
            return

        file_path = PLOTS_PATH / name
        if not file_path.is_file():
            self.send_bytes(404, b"Map not found", "text/plain; charset=utf-8")
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "text/html"
        self.send_bytes(200, file_path.read_bytes(), content_type)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Rainmapper generated HTML maps.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), RainmapperHandler)
    print(f"Rainmapper map server listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
