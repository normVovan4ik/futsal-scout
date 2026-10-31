import os

path = r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\app.js"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"app.js lines: {len(lines)}")
# Check for duplicate function definitions or syntax anomalies
funcs = [l.strip() for l in lines if l.strip().startswith("function ")]
print(f"Found {len(funcs)} functions:")
for fn in funcs:
    print(" ", fn[:50])
