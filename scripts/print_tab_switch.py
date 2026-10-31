import urllib.request
import json
import asyncio
import websockets
import subprocess
import time

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
proc = subprocess.Popen([
    edge_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "http://localhost:8000/"
])
time.sleep(2)

async def check():
    req = urllib.request.urlopen("http://localhost:9222/json")
    tabs = json.loads(req.read().decode())
    target = [t for t in tabs if "localhost:8000" in t.get("url", "")][0]
    async with websockets.connect(target["webSocketDebuggerUrl"]) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "switchTab('favorites'); JSON.stringify({playerCardHidden: document.getElementById('tab-player-card').classList.contains('hidden'), favHidden: document.getElementById('tab-favorites').classList.contains('hidden')})"
            }
        }))
        for _ in range(5):
            msg = await asyncio.wait_for(ws.recv(), timeout=2)
            d = json.loads(msg)
            if d.get("id") == 2:
                print("SWITCH TAB RESULT:", d["result"]["result"]["value"])
                break

try:
    asyncio.run(check())
finally:
    proc.terminate()
