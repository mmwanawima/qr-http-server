from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import os
import qrcode
from urllib.parse import unquote
import json
import traceback
from datetime import datetime

# =========================================================
# BASE SETUP
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "server_error.log")


# =========================================================
# LOAD CONFIG
# =========================================================
def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


cfg = load_config()

PORT = cfg["PORT"]
SHARE_FOLDER = cfg["SHARE_FOLDER"]
QR_FILENAME = cfg["QR_FILENAME"]


# =========================================================
# ERROR LOGGING (for EXE debugging)
# =========================================================
def log_error(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now()}] {msg}\n")


def log_exception():
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write(str(datetime.now()) + "\n")
        f.write(traceback.format_exc())
        f.write("\n")


# Catch ALL unhandled exceptions
def global_excepthook(exctype, value, tb):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 60 + "\n")
        f.write(str(datetime.now()) + "\n")
        f.write("".join(traceback.format_exception(exctype, value, tb)))


import sys
sys.excepthook = global_excepthook


# =========================================================
# GET LOCAL IP
# =========================================================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


local_ip = get_local_ip()
url = f"http://{local_ip}:{PORT}"


# =========================================================
# GENERATE QR CODE
# =========================================================
qr_path = os.path.join(BASE_DIR, QR_FILENAME)

qr = qrcode.make(url)
qr.save(qr_path)

log_error(f"QR generated at {url}")
log_error(f"Serving folder: {SHARE_FOLDER}")


# =========================================================
# HTTP SERVER HANDLER
# =========================================================
class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):

        try:

            # =========================================================
            # 0. Serve QR image
            # =========================================================
            if self.path.lstrip("/") == QR_FILENAME:
                qr_file = os.path.join(BASE_DIR, QR_FILENAME)

                if os.path.isfile(qr_file):
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.end_headers()

                    with open(qr_file, "rb") as f:
                        self.wfile.write(f.read())
                    return

            # =========================================================
            # 1. Resolve path
            # =========================================================
            requested_path = unquote(self.path.lstrip("/"))
            target_path = os.path.normpath(os.path.join(SHARE_FOLDER, requested_path))

            # =========================================================
            # 2. Security check
            # =========================================================
            if os.path.commonpath(
                [os.path.abspath(target_path), os.path.abspath(SHARE_FOLDER)]
            ) != os.path.abspath(SHARE_FOLDER):
                self.send_error(403, "Forbidden")
                return

            # =========================================================
            # 3. Directory listing
            # =========================================================
            if os.path.isdir(target_path):

                files = sorted(os.listdir(target_path))
                html = self._get_html_header()

                if requested_path:
                    parent = os.path.dirname(requested_path)
                    html += f'<div class="file"><a href="/{parent}">⬅️ Back</a></div>'

                for item in files:
                    item_path = os.path.join(target_path, item)
                    link = f"/{os.path.join(requested_path, item)}".replace("\\", "/")

                    if os.path.isdir(item_path):
                        html += f"""
                        <div class="file">
                            📁 <a href="{link}">{item}/</a>
                        </div>
                        """
                    else:
                        html += f"""
                        <div class="file">
                            📄 {item}
                            <a href="{link}">
                                <button>Download</button>
                            </a>
                        </div>
                        """

                html += "</div></body></html>"
                self._send_html(html)
                return

            # =========================================================
            # 4. File download
            # =========================================================
            if os.path.isfile(target_path):

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{os.path.basename(target_path)}"'
                )
                self.end_headers()

                with open(target_path, "rb") as f:
                    while chunk := f.read(64 * 1024):
                        self.wfile.write(chunk)

                return

            self.send_error(404, "Not Found")

        except Exception:
            log_exception()
            self.send_error(500, "Internal Server Error")


    # =========================================================
    # HTML UI
    # =========================================================
    def _get_html_header(self):
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>QR File Server</title>

<style>
body {{
    font-family: Arial;
    background: #f4f4f4;
    margin: 0;
    padding: 20px;
}}

.container {{
    max-width: 700px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,.1);
}}

h1 {{
    text-align: center;
}}

.file {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    margin: 8px 0;
    background: #eee;
    border-radius: 6px;
}}

button {{
    padding: 8px 12px;
    cursor: pointer;
}}

a {{
    text-decoration: none;
    color: #333;
}}

.qr {{
    text-align: center;
    margin: 20px 0;
}}
</style>
</head>

<body>

<div class="qr">
    <h3>📱 Scan QR Code</h3>
    <img src="/{QR_FILENAME}" width="220">
</div>

<div class="container">
    <h1>📁 QR File Server</h1>
"""


    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


# =========================================================
# START SERVER
# =========================================================
try:
    with HTTPServer(("", PORT), Handler) as httpd:
        print(f"Server running at {url}")
        log_error(f"Server started at {url}")
        httpd.serve_forever()

except Exception:
    log_exception()