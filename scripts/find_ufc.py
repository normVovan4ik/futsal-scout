with open(r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\app.js", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'updateFavoritesCounter', text)]
print("updateFavoritesCounter occurrences:", len(matches))
for m in matches:
    line_no = text[:m].count('\n') + 1
    print(f" line {line_no}: {text[m:m+60]}")
