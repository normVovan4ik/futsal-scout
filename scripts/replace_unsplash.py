import re

# Красивый силуэт футболиста в формате Data URI (SVG)
SVG_AVATAR = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>"

# Для каждого файла заменяем unsplash на локальный SVG
for fname in ["index.html", "app.js"]:
    fpath = rf"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\{fname}"
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()

    # Заменяем все unsplash ссылки
    new_text = re.sub(r'https://images\.unsplash\.com[^\s"\'<>]*', SVG_AVATAR, text)

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(new_text)

    print(f"Replaced unsplash in {fname} -> OK!")
