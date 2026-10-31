import subprocess
import time
import json
import urllib.request

# Start Edge in headless debugging mode
edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
proc = subprocess.Popen([
    edge_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "http://localhost:8000/"
])

time.sleep(3)

try:
    # Get DevTools websocket URL
    req = urllib.request.urlopen("http://localhost:9222/json")
    tabs = json.loads(req.read().decode())
    print("DevTools tabs found:", len(tabs))
    for t in tabs:
        print("  Tab:", t.get("title"), "URL:", t.get("url"))
except Exception as e:
    print("DevTools err:", e)
finally:
    proc.terminate()
