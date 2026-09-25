from http.server import BaseHTTPRequestHandler
import urllib.request

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            req=urllib.request.Request("https://api.thaistock2d.com/live",headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=10) as r:
                data=r.read()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write((str(e)).encode())
