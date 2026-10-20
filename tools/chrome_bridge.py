"""Local-only bridge to the Jarvis Chrome extension, routed by Chrome profile."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue, Empty
from threading import Thread, Lock
import json, secrets, time, urllib.parse, urllib.request
import os

HOST, PORT = "127.0.0.1", 31419
# Must match browser_extension/config.js. Localhost-only; do not expose this port publicly.
TOKEN = os.getenv("JARVIS_BRIDGE_TOKEN", "")

if not TOKEN:
    raise RuntimeError(
        "JARVIS_BRIDGE_TOKEN is missing. Set it in your local .env file."
    )
PROFILES = {"work", "main", "n8n"}
_queues = {p: Queue() for p in PROFILES}
_results, _lock, _started = {}, Lock(), False

def _start_server():
    global _started
    if _started: return
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def send_json(self, status, obj):
            data=json.dumps(obj).encode(); self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin","*")
            self.send_header("Access-Control-Allow-Headers","Content-Type, X-Jarvis-Token")
            self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS")
            self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
        def auth(self): return secrets.compare_digest(self.headers.get("X-Jarvis-Token",""),TOKEN)
        def do_OPTIONS(self): self.send_json(200,{"ok":True})
        def do_GET(self):
            if not self.auth(): return self.send_json(403,{"success":False,"error":"Unauthorized"})
            parsed=urllib.parse.urlparse(self.path); profile=urllib.parse.parse_qs(parsed.query).get("profile",["main"])[0]
            if parsed.path == "/health": return self.send_json(200,{"success":True,"message":"Jarvis bridge online"})
            if parsed.path == "/next":
                if profile not in PROFILES: return self.send_json(400,{"success":False,"error":"Unknown profile"})
                try: cmd=_queues[profile].get(timeout=15)
                except Empty: cmd=None
                return self.send_json(200,{"command":cmd})
            return self.send_json(404,{"error":"Not found"})
        def do_POST(self):
            if not self.auth(): return self.send_json(403,{"success":False,"error":"Unauthorized"})
            try: body=json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
            except Exception: return self.send_json(400,{"success":False,"error":"Invalid JSON"})
            path=urllib.parse.urlparse(self.path).path
            if path=="/command":
                profile=body.get("profile","main"); action=body.get("action"); args=body.get("args",{})
                allowed={"tabs","active_tab","navigate","click","fill","press","read","find_click","find_fill","click_first_video","video_seek"}
                if profile not in PROFILES or action not in allowed or not isinstance(args,dict): return self.send_json(400,{"success":False,"error":"Invalid profile, action, or arguments"})
                cid=secrets.token_urlsafe(12); _queues[profile].put({"id":cid,"action":action,"args":args})
                deadline=time.time()+25
                while time.time()<deadline:
                    with _lock: result=_results.pop(cid,None)
                    if result is not None: return self.send_json(200,result)
                    time.sleep(.1)
                return self.send_json(504,{"success":False,"error":f"Timed out. Check that the Jarvis extension is enabled in the '{profile}' Chrome profile and its profile selector is set correctly."})
            if path=="/result":
                cid=body.get("id")
                if not isinstance(cid,str): return self.send_json(400,{"success":False,"error":"Missing command id"})
                with _lock: _results[cid]=body.get("result",{"success":False,"error":"Empty result"})
                return self.send_json(200,{"success":True})
            return self.send_json(404,{"error":"Not found"})
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    Thread(target=server.serve_forever,daemon=True).start(); _started=True

def chrome_command(action, profile="main", **args):
    # Normalize profile names received from the AI.
    if not isinstance(profile, str):
        return {
            "success": False,
            "error": "Profile must be a string.",
        }

    profile = profile.strip().lower()
    words = profile.replace("-", " ").replace("_", " ").split()

    matched_profile = next(
        (name for name in PROFILES if name in words),
        None,
    )

    if matched_profile:
        profile = matched_profile

    if profile not in PROFILES:
        return {
            "success": False,
            "error": f"Profile must be one of {sorted(PROFILES)}",
        }

    _start_server()
    data = json.dumps({
        "profile": profile,
        "action": action,
        "args": args,
    }).encode()

    req = urllib.request.Request(
        f"http://{HOST}:{PORT}/command",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Jarvis-Token": TOKEN,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except Exception as error:
        return {
            "success": False,
            "error": f"Bridge error: {type(error).__name__}: {error}",
        }

def bridge_status():
    _start_server()
    return {"success":True,"host":HOST,"port":PORT,"profiles":sorted(PROFILES),"message":"Bridge running. Set the extension dropdown to the same profile you want Jarvis to control."}

def chrome_tabs(profile="main"): return chrome_command("tabs",profile=profile)
def chrome_active_tab(profile="main"): return chrome_command("active_tab",profile=profile)
def chrome_navigate(url, profile="main", new_tab=False):
    return chrome_command(
        "navigate",
        profile=profile,
        url=url,
        new_tab=new_tab,
    )
def chrome_click(selector,profile="main"): return chrome_command("click",profile=profile,selector=selector)
def chrome_fill(selector,text,profile="main"): return chrome_command("fill",profile=profile,selector=selector,text=text)
def chrome_press(key="Enter",selector="",profile="main"): return chrome_command("press",profile=profile,key=key,selector=selector)
def chrome_read(selector="body",profile="main"): return chrome_command("read",profile=profile,selector=selector)
def chrome_find_click(text,profile="main"): return chrome_command("find_click",profile=profile,text=text)
def chrome_find_fill(label,text,profile="main"): return chrome_command("find_fill",profile=profile,label=label,text=text)
def chrome_click_first_video(profile="main"): return chrome_command("click_first_video",profile=profile)
def chrome_video_seek(seconds=30,profile="main"): return chrome_command("video_seek",profile=profile,seconds=seconds)
