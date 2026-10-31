import re

for filename in ["index.html", "app.js", "db.py"]:
    filepath = rf"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\{filename}"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    found = re.findall(r'https://images\.unsplash\.com[^\s"\'<>]*', content)
    print(f"{filename}: found {len(found)} unsplash URLs")
    for u in set(found):
        print("  ", u[:60])
