import os
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

MYANMAR = timezone(timedelta(hours=6, minutes=30))
ENDPOINT = "https://www.htayapi.com/twod/thai/2dlive"
DEMO_DAY = "2026-11-27"

def digit(value):
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 99:
        return str(value).zfill(2)
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,2}", value.strip()):
        return value.strip().zfill(2)
    return None

def parse_date(value):
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None

def normalize(payload, now):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("invalid_schema")
    data = payload["data"]
    day = now.date().isoformat()
    source_date = parse_date(data.get("date"))
    out = {"date": day, "source_date": source_date, "source": "Htay API",
           "morning": {}, "afternoon": {}}
    if source_date != day:
        out["status"] = "date_mismatch"
        return out
    number = digit(data.get("live"))
    set_value = str(data.get("live_set") or "").strip()
    trade_value = str(data.get("live_val") or "").strip()
    numeric = r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?"
    if number is not None and re.fullmatch(numeric, set_value) and re.fullmatch(numeric, trade_value):
        closed = (now.hour, now.minute) >= (16, 30)
        final = digit(data.get("result_430"))
        final_stamp = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[/ T](?:16|4):30(?::00)?", str(data.get("time_430") or ""))
        final_ok = bool(closed and number == final and final_stamp and final_stamp.group(1) == day)
        current_time = str(data.get("current_time") or "")
        try:
            observed = datetime.strptime(day + " " + current_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=MYANMAR)
            observed_ok = -5 <= (now - observed).total_seconds() <= 90
        except ValueError:
            observed_ok = False
        if final_ok or observed_ok:
            out["live"] = {"twod": number, "set": set_value, "value": trade_value,
                           "date": day, "time": day + " 16:30:00" if final_ok else day + " " + current_time,
                           "time_kind": "final_result" if final_ok else "source_clock",
                           "observed_at": now.isoformat(), "final": final_ok}
    for slot, suffix, time in (("morning", "930", (9, 30)),
                               ("afternoon", "200", (14, 0))):
        if (now.hour, now.minute) >= time:
            out[slot] = {kind: digit(data.get(kind + "_" + suffix))
                         for kind in ("modern", "internet")}
    out["status"] = "ok" if any(v is not None for slot in ("morning", "afternoon")
                                for v in out[slot].values()) else "pending"
    return out

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        now = datetime.now(MYANMAR)
        day = now.date().isoformat()
        key = os.environ.get("HTAY_API_KEY", "").strip()
        demo = not key and day == DEMO_DAY
        if not key and not demo:
            return self.reply(503, {"error": "HTAY_API_KEY not configured"}, 0)
        if demo:
            key = "demoapi"
        ttl = min(3600 if demo else 60, max(0, 86400 - now.hour*3600 - now.minute*60 - now.second))
        try:
            req = urllib.request.Request(
                ENDPOINT, headers={"X-HtayApi-Key": key, "Accept": "application/json",
                                   "User-Agent": "MM2D/1.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.load(response)
            result = normalize(payload, now)
            result["mode"] = "sandbox" if demo else "production"
            self.reply(200, result, ttl)
        except urllib.error.HTTPError as exc:
            self.failure(day, demo, ttl, "upstream_http_" + str(exc.code))
        except (ValueError, TypeError):
            self.failure(day, demo, ttl, "invalid_upstream_response")
        except Exception:
            self.failure(day, demo, ttl, "upstream_unavailable")

    def failure(self, day, demo, ttl, reason):
        # Sandbox testing is deliberately cached; do not retry every client poll.
        self.reply(200 if demo else 502, {"date": day, "source": "Htay API",
                   "mode": "sandbox" if demo else "production", "status": reason,
                   "morning": {}, "afternoon": {}}, ttl if demo else 0)

    def reply(self, status, data, ttl):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=30, s-maxage=" + str(ttl) if ttl else "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
