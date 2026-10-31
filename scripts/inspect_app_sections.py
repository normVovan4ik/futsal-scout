# Script to generate clean, verified app.js with multi-account merging and team selectors
path = r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\app.js"

with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Let's inspect where doGlobalSearch begins and replace the search & card loading section
pos_search = text.find("// Глобальный поиск")
pos_presets = text.find("// Состояние и пресеты")

print("Found search at:", pos_search)
print("Found presets at:", pos_presets)
