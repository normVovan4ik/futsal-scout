import requests
import time

cdns = [
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/chart.js',
    'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js',
    'https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js'
]
for c in cdns:
    t0 = time.time()
    try:
        r = requests.get(c, timeout=5)
        print(f"{r.status_code} ({time.time()-t0:.2f}s): {c}")
    except Exception as e:
        print(f"FAIL ({time.time()-t0:.2f}s): {c} -> {e}")
