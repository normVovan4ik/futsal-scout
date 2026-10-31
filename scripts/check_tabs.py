import re

with open(r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\index.html", "r", encoding="utf-8") as f:
    html = f.read()

print("Buttons with switchTab:")
for m in re.findall(r'onclick=[\'"]switchTab\([^\)]+\)[\'"]', html):
    print(" ", m)

print("\nDivs with id=tab-:")
for m in re.findall(r'<div[^>]+id=[\'"](tab-[^\'"]+)[\'"]', html):
    print(" ", m)

print("\nElements with class tab-content:")
for m in re.findall(r'<div[^>]+class=[\'"][^\'"]*tab-content[^\'"]*[\'"][^>]*>', html):
    print(" ", m[:70])
