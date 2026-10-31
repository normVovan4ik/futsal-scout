import sys
import json
sys.path.insert(0, r'C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout')

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import server

res = server.search_all_sources('Ершов')
print(f"Results found: {len(res)}")
print(json.dumps(res, indent=2, ensure_ascii=False))
