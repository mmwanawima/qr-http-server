from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import os
import qrcode
import config
from urllib.parse import unquote

PORT = config.PORT
SHARE_FOLDER = config.SHARE_FOLDER


# -----------------------------
# Get correct LAN IP
# -----------------------------
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


local_ip = get_local_ip()
url = f"http://{local_ip}:{PORT}"


# -----------------------------
# Generate QR Code
# -----------------------------
qr = qrcode.make(url)
qr.save(os.path.join(os.path.dirname(__file__), config.QR_FILENAME))

print(f"QR code generated for: {url}")
print(f"Serving files from: {SHARE_FOLDER}")


# -----------------------------
# Set server root to project folder
# -----------------------------
os.chdir(os.path.dirname(__file__))


# -----------------------------
# Custom HTTP Handler
# -----------------------------
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Clean the path and get the full target path
        requested_path = unquote(self.path.lstrip('/'))
        target_path = os.path.normpath(os.path.join(SHARE_FOLDER, requested_path))

        # Ensure we stay within the SHARE_FOLDER (Security)
        if not target_path.startswith(os.path.abspath(SHARE_FOLDER)):
            self.send_error(403, "Forbidden")
            return


        # 0. Serve QR image (STATIC ASSET FIRST)
        if self.path == "/fileserver_qr.png":
            qr_path = os.path.join(os.path.dirname(__file__), "fileserver_qr.png")

            if os.path.isfile(qr_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()

                with open(qr_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        

        # 1. Handle directory listing
        if os.path.isdir(target_path):
            files = sorted(os.listdir(target_path))
            
            html = self._get_html_header()
            
            # Add "Back" link if we are in a subfolder
            if requested_path:
                parent = os.path.dirname(requested_path)
                html += f'<div class="file"><span>⬅️ <a href="/{parent}">Back</a></span></div>'

            for item in files:
                item_path = os.path.join(target_path, item)
                link = f"/{os.path.join(requested_path, item)}".replace("\\", "/")
                
                if os.path.isdir(item_path):
                    html += f'<div class="file"><span>📁 <a href="{link}">{item}/</a></span></div>'
                else:
                    html += f'''
                    <div class="file">
                        <span>📄 {item}</span>
                        <a href="{link}"><button>Download</button></a>
                    </div>'''

            html += "</div></body></html>"
            self._send_html(html)
            return

        # 2. Handle file download
        elif os.path.isfile(target_path):
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(target_path)}"')
            self.end_headers()
            with open(target_path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    self.wfile.write(chunk)
            return

        self.send_error(404, "File/Folder not found")

    def _get_html_header(self):
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QR File Server</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; margin: 0; padding: 20px; }
        .container { max-width: 700px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,.1); }
        h1 { text-align: center; }
        .file { display: flex; justify-content: space-between; align-items: center; padding: 12px; margin: 8px 0; background: #eeeeee; border-radius: 6px; }
        button { padding: 8px 15px; cursor: pointer; }
        a { text-decoration: none; color: #333; }
    </style>
</head>
<body>

    <div style="text-align:center; margin-top:20px;">
        <h3>Scan QR Code</h3>
        <img src="/fileserver_qr.png" style="width:250px;">
    </div>

    <div class="container">
        <h1>📁 QR File Server</h1>
"""

    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=UTF-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
        
        
# -----------------------------
# Start server
# -----------------------------
with HTTPServer(("", PORT), Handler) as httpd:
    print(f"Server running at {url}")
    httpd.serve_forever()
    