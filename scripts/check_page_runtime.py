import subprocess
import time
import json
import urllib.request
import asyncio
try:
    import websockets
except ImportError:
    pass

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
    import websockets
    req = urllib.request.urlopen("http://localhost:9222/json")
    tabs = json.loads(req.read().decode())
    target = [t for t in tabs if "localhost:8000" in t.get("url", "")][0]
    ws_url = target["webSocketDebuggerUrl"]
    print("Connecting to ws:", ws_url)
    async with websockets.connect(ws_url) as ws:
        # Enable console and runtime
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.send(json.dumps({"id": 2, "method": "Log.enable"}))
        
        # Evaluate typeof switchTab
        await ws.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {"expression": "typeof switchTab"}
        }))

        # Evaluate document.getElementById('tab-player-card').className
        await ws.send(json.dumps({
            "id": 4,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.getElementById('tab-player-card').className"}
        }))

        # Call switchTab('head-to-head')
        await ws.send(json.dumps({
            "id": 5,
            "method": "Runtime.evaluate",
            "params": {"expression": "switchTab('head-to-head'); document.getElementById('tab-player-card').className + ' | ' + document.getElementById('tab-head-to-head').className"}
        }))

        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(msg)
                if data.get("id") in [3, 4, 5]:
                    print(f"RES {data['id']}:", data.get("result", {}).get("result", {}).get("value"))
                elif data.get("method") == "Runtime.exceptionThrown":
                    print("EXCEPTION:", data)
                elif data.get("method") == "Runtime.consoleAPICalled":
                    print("CONSOLE:", data.get("params", {}).get("type"), [a.get("value") for a in data.get("params", {}).get("args", [])])
            except asyncio.TimeoutError:
                break

try:
    asyncio.run(check())
finally:
    proc.terminate()
