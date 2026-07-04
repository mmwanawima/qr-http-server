import http.server
import socketserver
import os
import socket
import qrcode
import config

PORT = config.PORT
SHARE_FOLDER = config.SHARE_FOLDER

# Change working directory to shared folder
os.chdir(SHARE_FOLDER)

# Automatically get local IP address
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

url = f"http://{local_ip}:{PORT}"

# Generate QR code
qr = qrcode.make(url)
qr.save(config.QR_FILENAME)
qr.show()

print(f"QR code generated for: {url}")
print(f"Serving '{SHARE_FOLDER}' at {url}")

# Start HTTP server
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
