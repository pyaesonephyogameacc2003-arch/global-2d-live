from http.server import BaseHTTPRequestHandler
import urllib.request
import json
from datetime import datetime, timezone, timedelta

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            req=urllib.request.Request("https://api.thaistock2d.com/live",headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req,timeout=10) as r:
                data=r.read()
            today=(datetime.now(timezone.utc)+timedelta(hours=6,minutes=30)).strftime("%Y-%m-%d")
            shwereq=urllib.request.Request("https://backend.shwelamin.com/api/lv/twod-result",headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(shwereq,timeout=10) as br: shwe=json.loads(br.read())
            bm=[]
            for x in shwe.get("data",[]):
                if x.get("date")==today: bm=[{"time":"09:30 AM","date":x.get("date"),"modern":x.get("modern_930","--"),"internet":x.get("internet_930","--")},{"time":"02:00 PM","date":x.get("date"),"modern":x.get("modern_200","--"),"internet":x.get("internet_200","--")}];break
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store, no-cache, must-revalidate")
            self.send_header("Pragma","no-cache")
            self.send_header("Expires","0")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            obj=json.loads(data);obj["bm2d"]=bm;self.wfile.write(json.dumps(obj).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write((str(e)).encode())
