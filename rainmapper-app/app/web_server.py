from __future__ import annotations

import argparse
import html
import mimetypes
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo


PLOTS_PATH = Path("/app/Plots")
LOG_PATH = Path("/share/rainmapper/last_run.log")
STATUS_PATH = Path("/share/rainmapper/status.txt")

RUN_LOCK = threading.Lock()
RUN_STATE = {
    "running": False,
    "action": "",
    "started_at": "",
    "finished_at": "",
    "exit_code": "",
    "last_message": "Ready.",
    "last_scheduled_date": "",
}


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def bool_env(name: str, default: bool = False) -> bool:
    value = env(name, "true" if default else "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


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
      --danger: #ff6b6b;
      --ok: #51cf66;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--fg);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 700;
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 18px;
    }}
    p {{
      color: var(--muted);
      margin: 0 0 16px;
      line-height: 1.45;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin: 16px 0 8px;
    }}
    .card,
    .empty,
    pre {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
    }}
    .card {{
      padding: 14px 16px;
    }}
    .label {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .value {{
      font-size: 16px;
      word-break: break-word;
    }}
    .ok {{ color: var(--ok); }}
    .danger {{ color: var(--danger); }}
    form {{
      display: inline-block;
      margin: 0 8px 8px 0;
    }}
    button {{
      min-height: 40px;
      padding: 0 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--fg);
      font: inherit;
    }}
    button:hover,
    button:focus {{
      border-color: var(--accent);
    }}
    button.primary {{
      background: #06344a;
      border-color: var(--accent);
    }}
    ul {{
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      gap: 10px;
    }}
    a.map-link {{
      display: block;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      color: var(--fg);
      text-decoration: none;
    }}
    a.map-link:focus,
    a.map-link:hover {{
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
      color: var(--muted);
    }}
    pre {{
      margin: 0;
      padding: 12px;
      overflow: auto;
      max-height: 360px;
      white-space: pre-wrap;
      font-size: 12px;
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


def get_timezone() -> ZoneInfo:
    timezone_name = env("RAINMAPPER_TIMEZONE", env("TZ", "Europe/Madrid"))
    try:
        return ZoneInfo(timezone_name)
    except Exception:
        return ZoneInfo("UTC")


def command_for(action: str) -> list[str]:
    update_command = [
        "python",
        "Rainmapper.py",
        "--create_meteoclimatic",
        env("RAINMAPPER_CREATE_METEOCLIMATIC", "true"),
        "--create_meteocat",
        env("RAINMAPPER_CREATE_METEOCAT", "true"),
        "--create_wunderground",
        env("RAINMAPPER_CREATE_WUNDERGROUND", "true"),
        "--days_init",
        env("RAINMAPPER_DAYS_INIT", "-7"),
        "--days_end",
        env("RAINMAPPER_DAYS_END", "0"),
        "--nomaps",
        env("RAINMAPPER_NOMAPS", "false"),
        "--nototals",
        env("RAINMAPPER_NOTOTALS", "false"),
        "--days_bucket",
        env("RAINMAPPER_DAYS_BUCKET", "10"),
        "--max_threads",
        env("RAINMAPPER_MAX_THREADS", "1"),
        "--max_attempts",
        env("RAINMAPPER_MAX_ATTEMPTS", "3"),
        "--meteoclimatic_pattern",
        env("RAINMAPPER_METEOCLIMATIC_PATTERN", "ESCAT"),
    ]

    if action == "update":
        return update_command
    if action == "maps":
        return ["python", "Rainmapper_Client.py"]
    if action == "all":
        return update_command + ["&&", "python", "Rainmapper_Client.py"]
    raise ValueError(f"Invalid action: {action}")


def run_action(action: str, source: str) -> bool:
    if action not in {"update", "maps", "all"}:
        return False

    with RUN_LOCK:
        if RUN_STATE["running"]:
            return False
        RUN_STATE.update(
            {
                "running": True,
                "action": action,
                "started_at": datetime.now(get_timezone()).isoformat(timespec="seconds"),
                "finished_at": "",
                "exit_code": "",
                "last_message": f"Running {action} from {source}.",
            }
        )

    thread = threading.Thread(target=_run_action_thread, args=(action, source), daemon=True)
    thread.start()
    return True


def _run_action_thread(action: str, source: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    started = datetime.now(get_timezone())

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n=== {started.isoformat(timespec='seconds')} - {action} ({source}) ===\n")
        log_file.flush()

        actions = ["update", "maps"] if action == "all" else [action]
        for current_action in actions:
            command = command_for(current_action)
            process = subprocess.Popen(
                command,
                cwd="/app",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="")
                log_file.write(line)
                log_file.flush()
            exit_code = process.wait()
            if exit_code != 0:
                break

        finished = datetime.now(get_timezone())
        log_file.write(f"=== finished with exit code {exit_code} at {finished.isoformat(timespec='seconds')} ===\n")

    message = "Finished successfully." if exit_code == 0 else f"Finished with exit code {exit_code}."
    with RUN_LOCK:
        RUN_STATE.update(
            {
                "running": False,
                "finished_at": datetime.now(get_timezone()).isoformat(timespec="seconds"),
                "exit_code": str(exit_code),
                "last_message": message,
            }
        )
    STATUS_PATH.write_text(message + "\n", encoding="utf-8")


def next_schedule_text() -> str:
    if not bool_env("RAINMAPPER_SCHEDULE_ENABLED"):
        return "Disabled"

    schedule_time = env("RAINMAPPER_SCHEDULE_TIME", "23:50")
    try:
        hour_text, minute_text = schedule_time.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return "Invalid schedule time"

    now = datetime.now(get_timezone())
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.isoformat(timespec="minutes")


def scheduler_loop() -> None:
    while True:
        time.sleep(20)
        if not bool_env("RAINMAPPER_SCHEDULE_ENABLED"):
            continue

        schedule_time = env("RAINMAPPER_SCHEDULE_TIME", "23:50")
        scheduled_action = env("RAINMAPPER_SCHEDULED_ACTION", "all")
        now = datetime.now(get_timezone())
        today_key = now.date().isoformat()

        if now.strftime("%H:%M") != schedule_time:
            continue
        if RUN_STATE["last_scheduled_date"] == today_key:
            continue
        if run_action(scheduled_action, "schedule"):
            RUN_STATE["last_scheduled_date"] = today_key


def tail_log(lines: int = 80) -> str:
    if not LOG_PATH.exists():
        return "No logs yet."
    content = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


class RainmapperHandler(BaseHTTPRequestHandler):
    server_version = "Rainmapper/0.2"

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_bytes(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def redirect_home(self) -> None:
        self.send_response(303)
        self.send_header("Location", "../")
        self.end_headers()

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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/run/"):
            action = path.removeprefix("/run/")
            run_action(action, "web")
            self.redirect_home()
            return

        self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")

    def render_index(self) -> None:
        with RUN_LOCK:
            running = RUN_STATE["running"]
            action = RUN_STATE["action"] or "-"
            message = RUN_STATE["last_message"]
            started_at = RUN_STATE["started_at"] or "-"
            finished_at = RUN_STATE["finished_at"] or "-"
            exit_code = RUN_STATE["exit_code"] or "-"

        status_class = "ok" if not running else "danger"
        status_text = "Running" if running else "Idle"
        disabled = "disabled" if running else ""

        controls = f"""
        <form method="post" action="run/update"><button {disabled}>Run update</button></form>
        <form method="post" action="run/maps"><button {disabled}>Generate maps</button></form>
        <form method="post" action="run/all"><button class="primary" {disabled}>Run all</button></form>
        """

        status = f"""
        <div class="grid">
          <div class="card"><span class="label">Status</span><span class="value {status_class}">{status_text}</span></div>
          <div class="card"><span class="label">Action</span><span class="value">{html.escape(action)}</span></div>
          <div class="card"><span class="label">Started</span><span class="value">{html.escape(started_at)}</span></div>
          <div class="card"><span class="label">Finished</span><span class="value">{html.escape(finished_at)}</span></div>
          <div class="card"><span class="label">Exit code</span><span class="value">{html.escape(exit_code)}</span></div>
          <div class="card"><span class="label">Next schedule</span><span class="value">{html.escape(next_schedule_text())}</span></div>
        </div>
        <p>{html.escape(message)}</p>
        """

        body = (
            "<h1>Rainmapper</h1>"
            "<p>Update weather data, generate maps, and browse generated HTML maps.</p>"
            "<h2>Actions</h2>"
            f"{controls}"
            "<h2>Status</h2>"
            f"{status}"
            "<h2>Maps</h2>"
            f"{self.render_map_list()}"
            "<h2>Last log</h2>"
            f"<pre>{html.escape(tail_log())}</pre>"
        )
        self.send_bytes(200, html_page("Rainmapper", body), "text/html; charset=utf-8")

    def render_map_list(self) -> str:
        files = sorted(PLOTS_PATH.glob("*.html"))
        if not files:
            return (
                '<div class="empty">No HTML maps found in '
                '<code>/share/rainmapper/Plots</code>.</div>'
            )

        items = []
        for file_path in files:
            stat = file_path.stat()
            name = file_path.name
            title = name.removesuffix(".html").replace("_", " ")
            items.append(
                "<li>"
                f'<a class="map-link" href="file/{html.escape(name)}">'
                f"{html.escape(title)}"
                f'<span class="meta">{html.escape(name)} - {format_size(stat.st_size)}</span>'
                "</a>"
                "</li>"
            )
        return "<ul>" + "".join(items) + "</ul>"

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

    scheduler = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler.start()

    server = ThreadingHTTPServer((args.host, args.port), RainmapperHandler)
    print(f"Rainmapper server listening on {args.host}:{args.port}")
    print(f"Schedule enabled: {bool_env('RAINMAPPER_SCHEDULE_ENABLED')}")
    print(f"Next schedule: {next_schedule_text()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
