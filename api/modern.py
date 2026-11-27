import os, json, re, urllib.request
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

def digit(value):
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 99:
        return str(value).zfill(2)
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,2}", value):
        return value.zfill(2)
    return None

def parse_date(value):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            pass
    return None

def normalize(data):
    date = parse_date(data.get("date"))
    now = datetime.now(timezone(timedelta(hours=6, minutes=30)))
    if date != now.date().isoformat():
        return {"date": date, "morning": {}, "afternoon": {}}
    def slot(suffixes, hour, minute):
        if (now.hour, now.minute) < (hour, minute):
            return {}
        return {kind: next((v for suffix in suffixes
                     if (v := digit(data.get(kind + "_" + suffix))) is not None), None)
                for kind in ("modern", "internet")}
    return {"date": date, "morning": slot(("930", "0930"), 9, 30),
            "afternoon": slot(("200", "1400", "0200"), 14, 0)}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        key = os.environ.get("SETLIVE_API_KEY")
        if not key:
            return self.reply(503, {"error": "Modern source not configured"})
        try:
            req = urllib.request.Request(
                "https://setlive.myanmarnode.com/api/v1/twod-result-live",
                headers={"X-API-Key": key, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.load(response)
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ValueError("Invalid source response")
            self.reply(200, normalize(data))
        except Exception:
            self.reply(502, {"error": "Modern source unavailable"})

    def reply(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=30, s-maxage=300" if status == 200 else "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
