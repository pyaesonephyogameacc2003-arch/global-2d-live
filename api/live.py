from http.server import BaseHTTPRequestHandler
import json, urllib.request

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with urllib.request.urlopen("https://api.thaistock2d.com/live", timeout=10) as r:
                data = r.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
