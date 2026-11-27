import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler

MYANMAR = timezone(timedelta(hours=6, minutes=30))
THAI_URL = "https://api.thaistock2d.com/live"
HTAY_PROXY = "https://global-2d-live.vercel.app/api/modern"

def fetch_json(url, timeout):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MM2D/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        return data if isinstance(data, dict) else None
    except Exception:
        return None

def select_live(thai, htay, now):
    day = now.date().isoformat()
    if not isinstance(thai, dict) or not isinstance(thai.get("live"), dict) or not isinstance(thai.get("result"), list):
        return None
    result = dict(thai)
    result["live_source"] = "ThaiStock2D"
    if not isinstance(htay, dict) or htay.get("source_date") != day:
        return result
    candidate = htay.get("live")
    if not isinstance(candidate, dict) or candidate.get("date") != day:
        return result
    number = str(candidate.get("twod") or "")
    numeric = r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?"
    if not re.fullmatch(r"\d{2}", number) or not all(re.fullmatch(numeric, str(candidate.get(k) or "")) for k in ("set", "value")):
        return result
    try:
        age = (now - datetime.fromisoformat(candidate["observed_at"])).total_seconds()
    except (KeyError, ValueError, TypeError):
        return result
    final = candidate.get("final") is True and (now.hour, now.minute) >= (16, 30)
    if not final and not 0 <= age <= 90:
        return result
    if htay.get("mode") == "sandbox" and not final:
        # The demo quota cannot support a 2-second market feed.
        return result
    original = thai["live"]
    def number_value(v):
        try:
            return float(str(v).replace(",", ""))
        except (TypeError, ValueError):
            return None
    same = (original.get("date") == day and str(original.get("twod")) == number
            and all(number_value(original.get(k)) == number_value(candidate[k]) for k in ("set", "value")))
    if final:
        confirmed = next((x for x in thai["result"] if isinstance(x, dict)
                          and str(x.get("open_time", "")).startswith("16:30")
                          and str(x.get("stock_datetime", "")).startswith(day)), None)
        if confirmed and str(confirmed.get("twod")) != number:
            result["live_fallback_reason"] = "final_result_conflict"
            return result
    result["live"] = {**original, "twod": number, "set": candidate["set"], "value": candidate["value"],
                      "date": day, "time": original.get("time") if same and original.get("time") else
                      candidate["time"] + ("" if final else " (Htay snapshot)")}
    result["live_source"] = "Htay API"
    result["live_source_mode"] = htay.get("mode")
    return result

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                thai_future = pool.submit(fetch_json, THAI_URL, 8)
                htay_future = pool.submit(fetch_json, HTAY_PROXY, 8)
                thai, htay = thai_future.result(), htay_future.result()
            result = select_live(thai, htay, datetime.now(MYANMAR))
            if result is None:
                return self.reply(502, {"error": "Live or confirmed results unavailable"})
            self.reply(200, result)
        except Exception:
            self.reply(502, {"error": "Live source unavailable"})

    def reply(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
