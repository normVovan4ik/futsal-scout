with open("C:/Users/ersov/.gemini/antigravity/scratch/futsal-scout/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add 'Команды' tab button
old_nav = """        <button onclick="switchTab('favorites')" id="tab-btn-favorites" class="tab-btn px-4 py-2 rounded-lg transition-all flex items-center gap-2 text-slate-400 hover:text-white">
          <i class="fa-solid fa-star text-amber-400"></i> Избранное (<span id="fav-counter">0</span>)
        </button>
        <button onclick="switchTab('head-to-head')" id="tab-btn-head-to-head" class="tab-btn px-4 py-2 rounded-lg transition-all flex items-center gap-2 text-slate-400 hover:text-white">
          <i class="fa-solid fa-bolt"></i> Дуэль (H2H)
        </button>"""

new_nav = """        <button onclick="switchTab('favorites')" id="tab-btn-favorites" class="tab-btn px-4 py-2 rounded-lg transition-all flex items-center gap-2 text-slate-400 hover:text-white">
          <i class="fa-solid fa-star text-amber-400"></i> Избранное (<span id="fav-counter">0</span>)
        </button>
        <button onclick="switchTab('teams-search')" id="tab-btn-teams-search" class="tab-btn px-4 py-2 rounded-lg transition-all flex items-center gap-2 text-slate-400 hover:text-white">
          <i class="fa-solid fa-shield-halved text-sky-400"></i> Команды (3 лиги)
        </button>
        <button onclick="switchTab('head-to-head')" id="tab-btn-head-to-head" class="tab-btn px-4 py-2 rounded-lg transition-all flex items-center gap-2 text-slate-400 hover:text-white">
          <i class="fa-solid fa-bolt"></i> Дуэль (H2H)
        </button>"""

content = content.replace(old_nav, new_nav)

# 2. Add custom photo upload controls under the 3D card
old_avatar_block = """                  <div class="w-36 h-44 rounded-2xl overflow-hidden relative border border-amber-400/30 bg-slate-900/60 flex items-center justify-center shadow-inner">
                    <img id="card-avatar" src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>" alt="Avatar" class="w-full h-full object-cover">
                    <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent"></div>
                  </div>"""

new_avatar_block = """                  <div class="w-36 h-44 rounded-2xl overflow-hidden relative border border-amber-400/30 bg-slate-900/60 flex items-center justify-center shadow-inner group/photo">
                    <img id="card-avatar" src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>" alt="Avatar" class="w-full h-full object-cover">
                    <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent pointer-events-none"></div>
                    <!-- Оверлей быстрой смены фото -->
                    <div class="absolute inset-0 bg-slate-950/80 opacity-0 group-hover/photo:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1.5 p-2 text-center cursor-pointer" onclick="document.getElementById('custom-avatar-file').click()">
                      <i class="fa-solid fa-camera text-amber-400 text-lg"></i>
                      <span class="text-[10px] font-bold text-white leading-tight">Сменить фото</span>
                    </div>
                  </div>"""

content = content.replace(old_avatar_block, new_avatar_block)

# 3. Add Photo action buttons under the card
old_buttons_block = """          <!-- Кнопка скачать карточку -->
          <button onclick="exportCard()" class="w-[320px] sm:w-[350px] py-3 px-5 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black flex items-center justify-center gap-3 shadow-lg shadow-amber-500/20 active:scale-95 transition">
            <i class="fa-solid fa-download"></i> Скачать карточку в PNG
          </button>"""

new_buttons_block = """          <!-- Блок управления фото игрока -->
          <div class="w-[320px] sm:w-[350px] mb-3 bg-slate-900/80 border border-slate-800 rounded-2xl p-3 flex items-center justify-between gap-2 shadow">
            <input type="file" id="custom-avatar-file" accept="image/*" class="hidden" onchange="handleAvatarFileUpload(event)">
            <button onclick="document.getElementById('custom-avatar-file').click()" class="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 border border-slate-700">
              <i class="fa-solid fa-image text-amber-400"></i> Загрузить фото
            </button>
            <button onclick="pasteAvatarFromClipboard()" class="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 border border-slate-700" title="Вставить из буфера обмена (Ctrl+V)">
              <i class="fa-solid fa-paste text-sky-400"></i> Вставить из буфера
            </button>
          </div>

          <!-- Кнопка скачать карточку -->
          <button onclick="exportCard()" class="w-[320px] sm:w-[350px] py-3 px-5 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black flex items-center justify-center gap-3 shadow-lg shadow-amber-500/20 active:scale-95 transition">
            <i class="fa-solid fa-download"></i> Скачать карточку в PNG
          </button>"""

content = content.replace(old_buttons_block, new_buttons_block)

# 4. Add Section for Teams Search Tab
teams_tab_html = """    <!-- ========================================== -->
    <!-- ВКЛАДКА: ПОИСК И СТАТИСТИКА КОМАНД        -->
    <!-- ========================================== -->
    <div id="tab-teams-search" class="tab-content hidden">
      <div class="mb-8 bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800 p-6 rounded-3xl shadow-xl">
        <div class="flex flex-col md:flex-row items-center justify-between gap-4">
          <div class="flex-1 w-full">
            <div class="flex items-center justify-between mb-2">
              <label class="block text-xs font-bold uppercase tracking-wider text-sky-400">
                <i class="fa-solid fa-shield-halved mr-1"></i> Поиск команды по всем 3 сайтам (Лига 5х5, Лига Старт, ФФГЭ):
              </label>
              <div class="flex gap-2 text-[11px] font-semibold text-slate-400">
                <span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">Лига 5х5</span>
                <span class="px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20">Лига Старт</span>
                <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">ФФГЭ</span>
              </div>
            </div>
            <div class="relative flex items-center">
              <input id="teams-search-input" type="text" placeholder="Введите название команды (например: Спортмастер, Рифей, Солянка, Полином)..." 
                     onkeydown="if(event.key==='Enter') doTeamsSearch()"
                     class="w-full bg-slate-950 border-2 border-slate-700 focus:border-sky-400 text-white rounded-2xl px-5 py-3.5 text-sm font-medium focus:outline-none transition shadow-inner">
              <button onclick="doTeamsSearch()" class="absolute right-2 px-5 py-2.5 bg-gradient-to-r from-sky-500 to-sky-600 hover:from-sky-400 hover:to-sky-500 text-slate-950 font-black rounded-xl text-xs transition active:scale-95 shadow">
                <i class="fa-solid fa-magnifying-glass mr-1"></i> Найти команду
              </button>
            </div>
          </div>
        </div>

        <div id="teams-search-results" class="hidden mt-6 pt-5 border-t border-slate-800">
          <div class="flex items-center justify-between mb-4">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-400" id="teams-results-heading">Результаты поиска команд:</span>
            <button onclick="document.getElementById('teams-search-results').classList.add('hidden')" class="text-xs text-slate-500 hover:text-white">Скрыть</button>
          </div>
          <div id="teams-search-cards" class="space-y-4">
            <!-- Динамические карточки команд -->
          </div>
        </div>
      </div>
    </div>
"""

old_h2h_tab = '    <div id="tab-head-to-head" class="tab-content hidden">'
content = content.replace(old_h2h_tab, teams_tab_html + "\n" + old_h2h_tab)

with open("C:/Users/ersov/.gemini/antigravity/scratch/futsal-scout/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html updated successfully!")
