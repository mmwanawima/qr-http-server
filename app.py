import http.server
import socketserver
import os
import socket
import qrcode

PORT = 8081
SHARE_FOLDER = r"C:\Users\youzer\Downloads\sharefile"

# Change working directory to shared folder
os.chdir(SHARE_FOLDER)

# Automatically get local IP address
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

url = f"http://{local_ip}:{PORT}"

# Generate QR code
qr = qrcode.make(url)
qr.save("fileserver_qr.png")
qr.show()

print(f"QR code generated for: {url}")
print(f"Serving '{SHARE_FOLDER}' at {url}")

# Start HTTP server
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
