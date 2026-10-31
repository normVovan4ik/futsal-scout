with open("C:/Users/ersov/.gemini/antigravity/scratch/futsal-scout/app.js", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update loadMergedPlayerToCard to automatically determine position based on stats
old_load = """  applyStatsToInputs({
    matches: player.total_matches,
    teamMatches: player.total_matches,
    goals: player.total_goals,
    assists: player.total_assists,
    yc: player.total_yellow_cards,
    rc: player.total_red_cards,
    mvp: player.total_mvp
  });"""

new_load = """  // Умный расчет амплуа (позиции) по реальной статистике
  let smartPos = "ALA";
  const g = player.total_goals || 0;
  const a = player.total_assists || 0;
  const m = Math.max(1, player.total_matches || 1);
  const yc = player.total_yellow_cards || 0;

  if (g / m >= 0.7 && g >= a) {
    smartPos = "PIV"; // Чистый бомбардир / столп
  } else if (a > g && a / m >= 0.4) {
    smartPos = "ALA"; // Распасовщик / бровка
  } else if (g / m < 0.25 && yc / m >= 0.15) {
    smartPos = "FIX"; // Защитник-разрушитель
  } else if (g === 0 && a === 0 && m > 3) {
    smartPos = "GK";  // Вратарь
  } else {
    smartPos = g >= a ? "PIV" : "ALA";
  }

  const posSelect = document.getElementById("input-pos");
  if (posSelect) posSelect.value = smartPos;

  // Если у игрока уже есть кастомный аватар в базе, подставляем его
  if (player.avatar) {
    document.getElementById("input-avatar").value = player.avatar;
    document.getElementById("card-avatar").src = player.avatar;
  }

  applyStatsToInputs({
    matches: player.total_matches,
    teamMatches: player.total_matches,
    goals: player.total_goals,
    assists: player.total_assists,
    yc: player.total_yellow_cards,
    rc: player.total_red_cards,
    mvp: player.total_mvp
  });"""

code = code.replace(old_load, new_load)

# 2. Add File upload and Clipboard paste handlers
avatar_handlers = """
// -----------------------------------------------------------------------------
// Кастомные фото: Загрузка из файла и вставка из буфера (Ctrl+V)
// -----------------------------------------------------------------------------
function handleAvatarFileUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  if (!file.type.startsWith("image/")) {
    alert("Пожалуйста, выберите файл изображения (JPG, PNG, WebP)!");
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    const dataUrl = e.target.result;
    applyCustomAvatar(dataUrl);
    alert("📸 Фото профиля успешно загружено!");
  };
  reader.readAsDataURL(file);
}

async function pasteAvatarFromClipboard() {
  try {
    const clipboardItems = await navigator.clipboard.read();
    for (const item of clipboardItems) {
      for (const type of item.types) {
        if (type.startsWith("image/")) {
          const blob = await item.getType(type);
          const reader = new FileReader();
          reader.onload = function(e) {
            applyCustomAvatar(e.target.result);
            alert("📋 Фото успешно вставлено из буфера обмена!");
          };
          reader.readAsDataURL(blob);
          return;
        }
      }
    }
    alert("В буфере обмена нет изображения. Сделайте скриншот или скопируйте картинку (Ctrl+C), затем нажмите эту кнопку.");
  } catch (err) {
    // Если Clipboard API запрещен, предлагаем вставить через prompt URL
    const url = prompt("Вставьте прямую ссылку на фото или Base64 Data URL:");
    if (url && url.trim().length > 5) {
      applyCustomAvatar(url.trim());
    }
  }
}

function applyCustomAvatar(dataUrl) {
  const avatarImg = document.getElementById("card-avatar");
  const avatarInput = document.getElementById("input-avatar");
  if (avatarImg) avatarImg.src = dataUrl;
  if (avatarInput) avatarInput.value = dataUrl;
  if (currentActivePlayer) currentActivePlayer.avatar = dataUrl;
  confetti({ particleCount: 30, spread: 50, origin: { y: 0.8 } });
}

// Глобальная поддержка горячей клавиши Ctrl+V для вставки картинки
window.addEventListener("paste", function(e) {
  const items = e.clipboardData && e.clipboardData.items;
  if (!items) return;
  for (let i = 0; i < items.length; i++) {
    if (items[i].type.indexOf("image") !== -1) {
      const blob = items[i].getAsFile();
      const reader = new FileReader();
      reader.onload = function(event) {
        applyCustomAvatar(event.target.result);
      };
      reader.readAsDataURL(blob);
      break;
    }
  }
});
"""

# 3. Add Teams Search function in app.js
teams_search_js = """
// -----------------------------------------------------------------------------
// Поиск и статистика команд (3 лиги)
// -----------------------------------------------------------------------------
async function doTeamsSearch() {
  const input = document.getElementById("teams-search-input");
  const query = (input ? input.value : "").trim();
  if (query.length < 2) {
    alert("Введите хотя бы 2 буквы названия команды (например, 'Спортмастер' или 'Рифей')");
    return;
  }

  const resultsBlock = document.getElementById("teams-search-results");
  const cardsContainer = document.getElementById("teams-search-cards");
  const heading = document.getElementById("teams-results-heading");

  resultsBlock.classList.remove("hidden");
  heading.innerText = "Поиск команды «" + query + "» по протоколам 3 лиг...";
  cardsContainer.innerHTML = '<div class="text-center py-6 text-slate-400"><i class="fa-solid fa-spinner fa-spin text-2xl text-sky-400 mb-2"></i><div class="text-sm">Сканируем таблицы лиг и турниров...</div></div>';

  const data = await fetchWithFallback(API_BASE + "/teams/search?q=" + encodeURIComponent(query));

  if (!data || !data.results) {
    cardsContainer.innerHTML = '<div class="text-center py-6 text-red-400 text-sm">Не удалось получить данные с сервера.</div>';
    return;
  }

  heading.innerText = "Найдено команд: " + data.count + " по запросу «" + query + "»";

  if (data.results.length === 0) {
    cardsContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-sm">Команда «' + query + '» не найдена. Попробуйте изменить название.</div>';
    return;
  }

  cardsContainer.innerHTML = "";
  data.results.forEach(team => {
    const cardEl = document.createElement("div");
    cardEl.className = "bg-slate-950 border border-slate-800 hover:border-sky-500/50 rounded-2xl p-5 transition shadow-lg flex flex-col gap-4";

    const leaguesBadges = team.sources_found.map(sName => {
      let color = "bg-amber-500/20 text-amber-300 border-amber-500/30";
      if (sName.indexOf("Старт") !== -1) color = "bg-sky-500/20 text-sky-300 border-sky-500/30";
      if (sName.indexOf("ФФГЭ") !== -1 || sName.indexOf("Наградион") !== -1) color = "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      return '<span class="px-2 py-0.5 rounded text-[10px] font-bold border ' + color + '">' + sName + '</span>';
    }).join(" ");

    const tournamentsListHtml = (team.tournaments || []).map(t => {
      return '<div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">' +
        '<div>' +
          '<div class="font-bold text-white flex items-center gap-2">' +
            '<span class="text-sky-400">🏆 ' + t.tournament_name + '</span>' +
            '<span class="text-slate-400 text-[10px]">(' + t.source_name + ')</span>' +
          '</div>' +
          '<div class="text-slate-300 mt-1">📊 Игр: <b>' + t.games + '</b> · Побед: <b>' + t.wins + '</b> · Забито: <b>' + t.goals + '</b>' +
            (t.points !== null && t.points !== undefined ? ' · Очков: <b class="text-amber-400">' + t.points + '</b>' : '') +
            (t.difference ? ' · Разница: <b>' + t.difference + '</b>' : '') +
          '</div>' +
        '</div>' +
        '<div class="flex items-center gap-3 shrink-0">' +
          '<div class="text-right">' +
            '<div class="text-[10px] text-slate-400 uppercase font-bold">Винрейт</div>' +
            '<div class="font-black ' + (t.winrate >= 60 ? 'text-emerald-400' : (t.winrate >= 40 ? 'text-amber-400' : 'text-slate-300')) + '">' + t.winrate + '%</div>' +
          '</div>' +
          (t.team_url ? '<a href="' + t.team_url + '" target="_blank" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-lg transition border border-slate-700">Профиль <i class="fa-solid fa-arrow-up-right-from-square ml-1 text-[10px]"></i></a>' : '') +
        '</div>' +
      '</div>';
    }).join("");

    cardEl.innerHTML = '<div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">' +
      '<div>' +
        '<div class="flex items-center gap-2 flex-wrap mb-1">' +
          '<h3 class="text-xl font-black text-white flex items-center gap-2">🛡️ ' + team.team_name + '</h3>' +
          leaguesBadges +
        '</div>' +
        '<p class="text-xs text-slate-400">Суммарная статистика по всем лигам и турнирам</p>' +
      '</div>' +
      '<div class="flex items-center gap-4 bg-slate-900 px-4 py-2 rounded-2xl border border-slate-800 text-center">' +
        '<div><div class="text-[10px] uppercase font-bold text-slate-400">Всего игр</div><div class="text-base font-black text-white">' + team.total_games + '</div></div>' +
        '<div class="w-px h-6 bg-slate-800"></div>' +
        '<div><div class="text-[10px] uppercase font-bold text-slate-400">Победы</div><div class="text-base font-black text-emerald-400">' + team.total_wins + '</div></div>' +
        '<div class="w-px h-6 bg-slate-800"></div>' +
        '<div><div class="text-[10px] uppercase font-bold text-slate-400">Голы</div><div class="text-base font-black text-amber-400">' + team.total_goals + '</div></div>' +
        '<div class="w-px h-6 bg-slate-800"></div>' +
        '<div><div class="text-[10px] uppercase font-bold text-slate-400">Винрейт</div><div class="text-base font-black text-sky-400">' + team.winrate + '%</div></div>' +
      '</div>' +
    '</div>' +
    '<div class="space-y-2">' +
      '<div class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Выступления в турнирах (' + team.tournaments.length + '):</div>' +
      tournamentsListHtml +
    '</div>';

    cardsContainer.appendChild(cardEl);
  });
}
"""

# 4. Update updateScoutText with rich diverse futsal facts & badges
old_scout_text = """function updateScoutText(p) {
  const summaryEl = document.getElementById("scout-summary");
  const tipEl = document.getElementById("coach-tip");

  let styleDesc = "";
  if (p.pos === "PIV") {
    styleDesc = "Классический пивот команды <b>" + p.team + "</b>. Наколотил <b>" + p.goals + " голов</b> за " + p.matches + " игр. Замыкает штанги и напрягает вратаря.";
  } else if (p.pos === "ALA") {
    styleDesc = "Мобильный крайний. Разогнал атаку и отдал <b>" + p.assists + " ассистов</b> за " + p.team + ".";
  } else if (p.pos === "FIX") {
    styleDesc = "Неуступчивый последний защитник. Руководит обороной, " + p.yc + " ЖК за сезон.";
  } else {
    styleDesc = "Вратарь команды " + p.team + ". Выручает в ближнем бою при выходах 1-на-1.";
  }

  let strongPoint = p.fin >= 85 ? "Смертоносное хладнокровие в штрафной." : (p.vis >= 85 ? "Идеальные пасы вразрез." : "Колоссальная самоотдача.");
  let riskPoint = p.disc < 70 ? "Риск привезти 10-метровый за перебор фолов." : (p.att < 75 ? "Нестабильная явка." : "Требует подстраховки в защите.");

  summaryEl.innerHTML = "<p><b>Стиль:</b> " + styleDesc + "</p>" +
    '<p class="text-emerald-400"><b>+ Сильная сторона:</b> ' + strongPoint + '</p>' +
    '<p class="text-amber-400"><b>⚠ Зона риска:</b> ' + riskPoint + '</p>';

  tipEl.innerText = p.pos === "PIV" 
    ? "Грузить мяч низом на него спиной к чужим воротам под сброс на набегающего."
    : (p.pos === "ALA" ? "Давать свободу обыгрывать один-в-один на бровке." : "Не фолить в центральном круге на 5-м командном фоле.");
}"""

new_scout_text = """function updateScoutText(p) {
  const summaryEl = document.getElementById("scout-summary");
  const tipEl = document.getElementById("coach-tip");

  const gPerMatch = (p.goals / Math.max(1, p.matches)).toFixed(2);
  const aPerMatch = (p.assists / Math.max(1, p.matches)).toFixed(2);
  const ptsPerMatch = ((p.goals + p.assists) / Math.max(1, p.matches)).toFixed(2);

  let archetype = "";
  let funnyFact = "";
  let styleDesc = "";

  if (p.pos === "PIV") {
    if (gPerMatch >= 1.5) {
      archetype = "🔥 Голевая машина (Король пятака)";
      funnyFact = "Вратарю соперника проще сразу достать мяч из сетки, чем спорить с ним на ленточке. Забивает чаще, чем судья успевает свистнуть.";
    } else if (p.goals > p.assists * 2) {
      archetype = "🎯 Наконечник копья";
      funnyFact = "Пас назад? Не слышал. Принимает мяч подошвой спиной к воротам и разворачивается с ударом с любого радиуса.";
    } else {
      archetype = "⚡ Универсальный форвард";
      funnyFact = "Полезен как на завершении (" + p.goals + " г.), так и в подыгрыше (" + p.assists + " пас.). Всегда дежурит на дальней штанге.";
    }
    styleDesc = "Пивот команды <b>" + p.team + "</b> с показателем <b>" + gPerMatch + " гола за игру</b> (всего " + p.goals + " г. в " + p.matches + " матчах).";
  } else if (p.pos === "ALA") {
    if (aPerMatch >= 0.7) {
      archetype = "🧙‍♂️ Профессор бровки (Плеймейкер)";
      funnyFact = "Видит партнёра ещё до того, как тот сам понял, куда побежит. Катит передачи сквозь троих защитников точно под удар в касание.";
    } else if (p.goals >= 10 && p.assists >= 10) {
      archetype = "⚡ Электровеник (Box-to-box 5х5)";
      funnyFact = "Успевает и отобрать у своих ворот, и прибежать на чужую половину замкнуть прострел. Двужильный мотор команды.";
    } else {
      archetype = "🌪️ Дриблер / Крайний полузащитник";
      funnyFact = "Любит качнуть защитника на ложном замахе подошвой и уйти в центр под рабочую ногу.";
    }
    styleDesc = "Мобильный вингер <b>" + p.team + "</b>. Генерирует <b>" + ptsPerMatch + " очка (Г+П) за матч</b> (" + p.goals + "г + " + p.assists + "п).";
  } else if (p.pos === "FIX") {
    if (p.yc >= 3 || p.rc > 0) {
      archetype = "🧱 Бетонная стена (Костолом района)";
      funnyFact = "Мяч может пройти, но нападающий — никогда. Арбитры знают его по имени и сразу держат желтую карточку наготове.";
    } else {
      archetype = "🧠 Тактический мозг обороны (Чистильщик)";
      funnyFact = "Читает чужие контратаки за две секунды до паса. Снимает верх, блокирует удары телом и никогда не привозит 10-метровые.";
    }
    styleDesc = "Последний защитник <b>" + p.team + "</b>. Сцементировал оборону в " + p.matches + " играх, совершая минимум лишних фолов.";
  } else {
    archetype = "🧤 Железный страж ворот";
    funnyFact = "Шпагаты на паркете выполняет лучше гимнастов. Если команда проигрывает за минуту до конца — уже бежит к чужой штрафной пятым полевым.";
    styleDesc = "Голкипер команды <b>" + p.team + "</b>. " + p.matches + " матчей на страже ворот.";
  }

  let strongPoint = p.fin >= 85 ? "Смертоносная реализация моментов в штрафной." : (p.vis >= 80 ? "Филигранное чтение игры и передачи вразрез." : (p.clutch >= 80 ? "Решает исходы валидольных матчей на последних секундах." : "Колоссальная самоотдача и объем беговой работы."));
  let riskPoint = p.yc >= 3 ? "Риск перебора командных фолов (опасность 10-метровых дабл-пенальти)." : (p.att < 75 ? "Нестабильный график явки на ранние утренние матчи." : "Иногда заигрывается и требует подстраховки при контратаках.");

  summaryEl.innerHTML = '<div class="mb-2"><span class="px-2.5 py-1 rounded-xl text-xs font-black bg-amber-500/20 text-amber-300 border border-amber-500/30">' + archetype + '</span></div>' +
    '<p class="text-slate-200"><b>Стиль:</b> ' + styleDesc + '</p>' +
    '<p class="text-amber-200/90 italic text-xs bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">«' + funnyFact + '»</p>' +
    '<p class="text-emerald-400"><b>+ Сильная сторона:</b> ' + strongPoint + '</p>' +
    '<p class="text-rose-400"><b>⚠ Зона риска:</b> ' + riskPoint + '</p>';

  tipEl.innerText = p.pos === "PIV" 
    ? "Грузить мяч низом на него спиной к чужим воротам под сброс на набегающего, либо искать прострелом на дальней штанге."
    : (p.pos === "ALA" ? "Давать свободу обыгрывать один-в-один на бровке и бить с носка в дальний угол." : (p.pos === "FIX" ? "Держать центральную зону и руководить выходом из-под прессинга." : "Играть шире и страховать створ при подключениях 5-м полевым."));
}"""

code = code.replace(old_scout_text, new_scout_text)

# Append avatar_handlers and teams_search_js to the end of app.js
code += "\n\n" + avatar_handlers + "\n\n" + teams_search_js

with open("C:/Users/ersov/.gemini/antigravity/scratch/futsal-scout/app.js", "w", encoding="utf-8") as f:
    f.write(code)

print("app.js updated successfully!")
