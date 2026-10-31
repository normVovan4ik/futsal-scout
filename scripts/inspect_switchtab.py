with open(r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\app.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Check for obvious syntax errors like unescaped backticks, bad chars
    if "\x00" in line:
        print(f"Null byte at line {i+1}")
    # Check for unterminated template strings
    if line.count("`") % 2 != 0:
        pass # could span multiple lines

print(f"Total lines: {len(lines)}")
# Print lines around switchTab
for i, line in enumerate(lines):
    if "function switchTab" in line:
        print(f"switchTab definition at line {i+1}:")
        for j in range(max(0, i-5), min(len(lines), i+30)):
            print(f"  {j+1}: {lines[j].rstrip()}")
