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
# hostname = socket.gethostname()
# local_ip = socket.gethostbyname(hostname)




def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

local_ip = get_local_ip()






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
