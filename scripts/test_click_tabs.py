import subprocess
import time
import json
import urllib.request
import asyncio
import websockets

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
proc = subprocess.Popen([
    edge_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "http://localhost:8000/"
])

time.sleep(3)

async def check():
    req = urllib.request.urlopen("http://localhost:9222/json")
    tabs = json.loads(req.read().decode())
    target = [t for t in tabs if "localhost:8000" in t.get("url", "")][0]
    ws_url = target["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        
        # 1. typeof switchTab
        await ws.send(json.dumps({
            "id": 10,
            "method": "Runtime.evaluate",
            "params": {"expression": "typeof switchTab"}
        }))

        # 2. Click switchTab('head-to-head') and check visibility
        await ws.send(json.dumps({
            "id": 20,
            "method": "Runtime.evaluate",
            "params": {"expression": "switchTab('head-to-head'); [document.getElementById('tab-player-card').classList.contains('hidden'), document.getElementById('tab-head-to-head').classList.contains('hidden')]"}
        }))

        # 3. Click switchTab('favorites')
        await ws.send(json.dumps({
            "id": 30,
            "method": "Runtime.evaluate",
            "params": {"expression": "switchTab('favorites'); [document.getElementById('tab-favorites').classList.contains('hidden')]"}
        }))

        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(msg)
                if data.get("id") in [10, 20, 30]:
                    print(f"ID {data['id']}:", data.get("result", {}).get("result"))
                elif data.get("method") == "Runtime.exceptionThrown":
                    print("LIVE EXCEPTION:", data)
            except asyncio.TimeoutError:
                break

try:
    asyncio.run(check())
finally:
    proc.terminate()
