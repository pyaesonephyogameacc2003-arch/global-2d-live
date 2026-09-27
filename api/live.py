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
            bmreq=urllib.request.Request("https://napi.bm2d.net/number/filter?date="+today,headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(bmreq,timeout=10) as br: bm=json.loads(br.read())
            for x in bm.get("data",[]):
                if x.get("time") in ("09:30 AM","02:00 PM"):
                    a=x.get("set","");v=x.get("value","");si=a.split(".")[0][-1:] if "." in a else a[-1:];vi=v.split(".")[0][-1:] if "." in v else v[-1:];sd=a.split(".")[1][-1:] if "." in a and len(a.split("."))>1 else "";vd=v.split(".")[1][-1:] if "." in v and len(v.split("."))>1 else "";x["modern"]=si+vi;x["internet"]=sd+vd
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store, no-cache, must-revalidate")
            self.send_header("Pragma","no-cache")
            self.send_header("Expires","0")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            obj=json.loads(data);obj["bm2d"]=[x for x in bm.get("data",[]) if x.get("time") in ("09:30 AM","02:00 PM")];self.wfile.write(json.dumps(obj).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write((str(e)).encode())
