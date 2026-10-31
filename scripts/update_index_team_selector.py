path = r"C:\Users\ersov\.gemini\antigravity\scratch\futsal-scout\index.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = """          <!-- Редактор статы игрока -->"""
addition = """          <!-- Переключатель команд игрока (Все команды vs Уралхиммаш vs Спортмастер) -->
          <div id="card-team-selector" class="hidden bg-slate-900/90 border border-amber-500/30 p-4 rounded-3xl shadow-lg">
            <div class="flex items-center justify-between mb-2.5">
              <div class="text-xs font-bold uppercase tracking-wider text-amber-300 flex items-center gap-2">
                <i class="fa-solid fa-shirt"></i> Выбор команды игрока:
              </div>
              <span id="active-team-badge" class="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">
                Все команды суммарно
              </span>
            </div>
            <div class="flex flex-wrap gap-2" id="team-toggle-buttons">
              <!-- Динамические кнопки команд -->
            </div>
          </div>

          <!-- Редактор статы игрока -->"""

if target in text:
    text = text.replace(target, addition)
    print("Replaced target in index.html!")
else:
    target_crlf = target.replace("\n", "\r\n")
    addition_crlf = addition.replace("\n", "\r\n")
    if target_crlf in text:
        text = text.replace(target_crlf, addition_crlf)
        print("Replaced CRLF target in index.html!")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated index.html!")
