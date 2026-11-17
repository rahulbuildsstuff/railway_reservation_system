"""
Local HTTP Web Server for the Railway Reservation System (RRS)
Serves `index.html` and provides a `/api/health` endpoint.
Usage: python3 src/server.py
"""
import http.server
import json
import os
import socketserver

PORT = 8000
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class RRSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "status": "OK",
                "system": "Railway Reservation System (RRS) v2.0",
                "student": "Nalla Rahul (00814803124)",
                "course": "CIC-357 Software Engineering"
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return
        return super().do_GET()


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), RRSRequestHandler) as httpd:
        print(f"🚆 Railway Reservation System server running at http://localhost:{PORT}")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()
