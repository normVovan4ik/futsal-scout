// =============================================================================
// Futsal Scout Hub - app.js v3.0
// Поддержка слияния аккаунтов одного игрока, переключения команд/дивизионов,
// расчета карточки FIFA 5х5 и сохранения в SQLite базу.
// =============================================================================

const API_BASE = "http://localhost:8000/api";

let allRealPlayers = [];
let currentSource = "liga5x5";
let currentSeason = null;

// Состояние текущего игрока на карточке
let currentActivePlayer = null;
let activePlayerSources = {};
let activePlayerTeams = {};
let activeTeamKey = "all";
let activeSourceKey = "all";

async function fetchWithFallback(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } catch (e) {
    console.warn("API недоступен:", e.message);
    return null;
  }
}

// -----------------------------------------------------------------------------
// Глобальный поиск по всем 3 сайтам
// -----------------------------------------------------------------------------
async function doGlobalSearch() {
  const input = document.getElementById("global-search-input");
  const query = (input ? input.value : "").trim();
  if (query.length < 2) {
    alert("Введите хотя бы 2 буквы для поиска (например, 'Ершов')");
    return;
  }

  const resultsBlock = document.getElementById("global-search-results");
  const cardsContainer = document.getElementById("global-search-cards");
  const heading = document.getElementById("search-results-heading");

  resultsBlock.classList.remove("hidden");
  heading.innerText = "Поиск по запросу «" + query + "» во всех 3 лигах...";
  cardsContainer.innerHTML = '<div class="text-center py-6 text-slate-400"><i class="fa-solid fa-spinner fa-spin text-2xl text-amber-400 mb-2"></i><div class="text-sm">Ищем игрока и проверяем все команды на сайтах Лиги 5х5, Лиги Старт и ФФГЭ...</div></div>';

  const data = await fetchWithFallback(API_BASE + "/search?q=" + encodeURIComponent(query));

  if (!data || !data.results) {
    cardsContainer.innerHTML = '<div class="text-center py-6 text-red-400 text-sm"><i class="fa-solid fa-triangle-exclamation mb-1"></i> Не удалось подключиться к серверу. Убедитесь, что server.py запущен.</div>';
    return;
  }

  heading.innerText = "Найдено игроков: " + data.count + " по запросу «" + query + "»";

  if (data.results.length === 0) {
    cardsContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-sm">Игрок «' + query + '» не найден в открытых протоколах 3 лиг. Попробуйте ввести только фамилию.</div>';
    return;
  }

  window.lastSearchResults = data.results || [];
  cardsContainer.innerHTML = "";
  data.results.forEach(player => {
    const cardEl = document.createElement("div");
    cardEl.className = "bg-slate-950 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-5 transition shadow-lg flex flex-col gap-4";

    const hasMultipleAccounts = player.accounts && player.accounts.length > 1;

    // Бейджи лиг
    const leaguesBadges = player.sources_found.map(sName => {
      let color = "bg-amber-500/20 text-amber-300 border-amber-500/30";
      if (sName.indexOf("Старт") !== -1) color = "bg-sky-500/20 text-sky-300 border-sky-500/30";
      if (sName.indexOf("ФФГЭ") !== -1 || sName.indexOf("Наградион") !== -1) color = "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
      return '<span class="px-2 py-0.5 rounded text-[10px] font-bold border ' + color + '">' + sName + '</span>';
    }).join(" ");

    // Список команд
    const teamsList = Object.keys(player.all_teams || {});
    const teamsBadges = teamsList.map(tname => {
      const t = player.all_teams[tname];
      return '<span class="px-2.5 py-1 rounded-xl bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-200">👕 <b>' + tname + '</b> <span class="text-amber-400 font-bold ml-1">' + t.matches + 'м, ' + t.goals + 'г</span></span>';
    }).join(" ");

    let multipleAccountsHtml = "";
    if (hasMultipleAccounts) {
      const accountsListHtml = player.accounts.map((acc, idx) => {
        const accTeams = (acc.teams || []).map(t => t.team_name + " (" + t.matches + "м, " + t.goals + "г)").join(", ") || "Команда не указана";
        return '<div class="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">' +
          '<div>' +
            '<div class="font-bold text-white flex items-center gap-2"><span class="text-amber-400">Аккаунт #' + (acc.account_id || idx+1) + '</span><span class="text-slate-400 font-normal">(' + acc.source_name + ')</span></div>' +
            '<div class="text-slate-300 mt-1">👕 <b>Команды:</b> ' + accTeams + '</div>' +
            '<div class="text-slate-400 mt-0.5">📊 ' + acc.matches + ' матчей · ' + acc.goals + ' голов · ' + acc.assists + ' ассистов · ' + acc.yellow_cards + ' ЖК</div>' +
          '</div>' +
          '<button onclick="loadSingleAccountById(' + player.accounts[idx].account_id + ')" class="shrink-0 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-lg transition border border-slate-700 hover:border-amber-500/40">Загрузить только этот аккаунт</button>' +
        '</div>';
      }).join("");

      multipleAccountsHtml = '<div class="mt-3 p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl">' +
        '<div class="flex items-center justify-between flex-wrap gap-2 mb-3">' +
          '<div class="text-xs font-bold text-amber-300 flex items-center gap-2"><i class="fa-solid fa-code-merge"></i> Найдено ' + player.accounts.length + ' аккаунта игрока «' + player.name + '». Вы можете объединить их в один общий профиль:</div>' +
          '<button class="btn-merge-all px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black text-xs rounded-xl shadow transition active:scale-95 flex items-center gap-1.5"><i class="fa-solid fa-link"></i> Слить аккаунты (' + player.total_matches + 'и, ' + player.total_goals + 'г)</button>' +
        '</div>' +
        '<div class="space-y-2">' + accountsListHtml + '</div>' +
      '</div>';
    }

    cardEl.innerHTML = '<div class="flex flex-col md:flex-row md:items-center justify-between gap-4">' +
      '<div class="flex-1 min-w-0">' +
        '<div class="flex items-center gap-2 flex-wrap mb-1.5">' +
          '<h4 class="text-lg font-black text-white hover:text-amber-300 transition">' + (player.full_name || player.name) + '</h4>' +
          '<div class="flex gap-1">' + leaguesBadges + '</div>' +
          (hasMultipleAccounts ? '<span class="px-2 py-0.5 rounded text-[10px] font-black bg-purple-500/20 text-purple-300 border border-purple-500/40">2+ аккаунта</span>' : '') +
        '</div>' +
        '<div class="text-xs text-slate-300 mb-2">' +
          '<span class="text-amber-400 font-bold">' + player.total_matches + '</span> матчей · ' +
          '<span class="text-amber-400 font-bold">' + player.total_goals + '</span> голов · ' +
          '<span class="text-sky-400 font-bold">' + player.total_assists + '</span> пасов · ' +
          '<span class="text-slate-400 font-bold">Г+П: ' + player.total_pts + '</span> · ' +
          '<span class="text-yellow-400 font-bold">ЖК: ' + player.total_yellow_cards + '</span>' +
          (player.total_mvp > 0 ? ' · <span class="text-emerald-400 font-bold">MVP: ' + player.total_mvp + '</span>' : '') +
        '</div>' +
        '<div class="flex flex-wrap gap-1.5 items-center"><span class="text-[11px] font-bold text-slate-400 uppercase mr-1">Команды:</span>' + (teamsBadges || '<span class="text-xs text-slate-500">Команда не указана</span>') + '</div>' +
      '</div>' +
      '<div class="flex items-center gap-2 shrink-0">' +
        '<button class="btn-load-main px-5 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 text-xs font-black rounded-xl transition shadow active:scale-95 flex items-center gap-1.5"><i class="fa-solid fa-id-card"></i> На карточку</button>' +
        '<button class="btn-fav-main px-3.5 py-2.5 bg-slate-900 hover:bg-slate-800 text-amber-400 border border-amber-500/30 text-xs font-bold rounded-xl transition active:scale-95" title="В избранное"><i class="fa-solid fa-star"></i></button>' +
      '</div>' +
    '</div>' + multipleAccountsHtml;

    cardEl.querySelector(".btn-load-main").onclick = () => loadMergedPlayerToCard(player);
    cardEl.querySelector(".btn-fav-main").onclick = () => savePlayerDirectlyToFavorites(player);
    const mergeBtn = cardEl.querySelector(".btn-merge-all");
    if (mergeBtn) {
      mergeBtn.onclick = () => mergeAndLoadPlayer(player);
    }

    cardsContainer.appendChild(cardEl);
  });
}

// -----------------------------------------------------------------------------
// Слияние аккаунтов одного игрока
// -----------------------------------------------------------------------------
function mergeAndLoadPlayer(player) {
  if (!player.accounts || player.accounts.length < 2) {
    loadMergedPlayerToCard(player);
    return;
  }

  // Строгая проверка совпадения ФИО
  const baseName = player.name.trim().toLowerCase();
  for (let acc of player.accounts) {
    if (player.name.trim().toLowerCase() !== baseName) {
      alert("Слияние отклонено! Имена и фамилии не совпадают: нельзя объединить аккаунты разных людей!");
      return;
    }
  }

  loadMergedPlayerToCard(player);
  alert("🔗 Успешно объединены " + player.accounts.length + " аккаунта игрока «" + player.name + "» со всеми его командами!");
}

function loadSingleAccountById(accId) {
  let foundPlayer = null;
  let targetAcc = null;

  const pool = (window.lastSearchResults || []);
  for (let p of pool) {
    if (p.accounts) {
      const acc = p.accounts.find(a => String(a.account_id) === String(accId));
      if (acc) {
        foundPlayer = p;
        targetAcc = acc;
        break;
      }
    }
  }

  if (!targetAcc && currentActivePlayer && currentActivePlayer.accounts) {
    targetAcc = currentActivePlayer.accounts.find(a => String(a.account_id) === String(accId));
    if (targetAcc) foundPlayer = currentActivePlayer;
  }

  if (!targetAcc) {
    alert("Аккаунт #" + accId + " не найден");
    return;
  }

  const singlePlayer = {
    name: foundPlayer.name,
    team: targetAcc.teams && targetAcc.teams.length > 0 ? targetAcc.teams[0].team_name : (targetAcc.source_name || "Команда"),
    all_teams: {},
    sources_data: { [targetAcc.source_id]: targetAcc },
    total_matches: targetAcc.matches,
    total_goals: targetAcc.goals,
    total_assists: targetAcc.assists,
    total_yellow_cards: targetAcc.yellow_cards,
    total_red_cards: targetAcc.red_cards,
    total_mvp: targetAcc.mvp_count || 0
  };

  (targetAcc.teams || []).forEach(t => {
    singlePlayer.all_teams[t.team_name] = t;
  });

  loadMergedPlayerToCard(singlePlayer);
}

function loadMergedPlayerToCard(player) {
  currentActivePlayer = player;
  activePlayerSources = player.sources_data || {};
  activePlayerTeams = player.all_teams || {};
  activeTeamKey = "all";
  activeSourceKey = "all";

  document.getElementById("input-name").value = player.name;
  
  const teamNames = Object.keys(activePlayerTeams);
  const primaryTeam = teamNames.length > 0 ? teamNames[0] : (player.team || "Любительская лига");
  document.getElementById("input-team").value = teamNames.length > 1 ? primaryTeam + " (+" + (teamNames.length - 1) + " ком.)" : primaryTeam;

  renderTeamFilterButtons(player);
  renderSourceFilterButtons(player);

  // Умный расчет амплуа (позиции) по реальной статистике
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
  });

  recalcCard();
  switchTab("player-card");

  confetti({ particleCount: 50, spread: 60, origin: { y: 0.7 } });
}

// -----------------------------------------------------------------------------
// Переключатель команд игрока на карточке
// -----------------------------------------------------------------------------
function renderTeamFilterButtons(player) {
  const container = document.getElementById("card-team-selector");
  const btnContainer = document.getElementById("team-toggle-buttons");
  const badge = document.getElementById("active-team-badge");

  if (!container || !btnContainer) return;

  const teams = Object.entries(player.all_teams || {});
  if (teams.length <= 1) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");
  btnContainer.innerHTML = "";

  const allBtn = document.createElement("button");
  allBtn.className = "team-toggle-btn px-3 py-1.5 rounded-xl text-xs font-black transition bg-amber-500 text-slate-950 shadow";
  allBtn.id = "btn-team-all";
  allBtn.innerHTML = "🏆 Все команды (" + player.total_matches + "и, " + player.total_goals + "г)";
  allBtn.onclick = () => selectCardTeam("all", player);
  btnContainer.appendChild(allBtn);

  teams.forEach(([tname, tdata]) => {
    const tBtn = document.createElement("button");
    tBtn.className = "team-toggle-btn px-3 py-1.5 rounded-xl text-xs font-bold transition bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-700";
    tBtn.id = "btn-team-" + tname.replace(/\s+/g, '_');
    tBtn.innerHTML = "👕 " + tname + " (" + tdata.matches + "и, " + tdata.goals + "г)";
    tBtn.onclick = () => selectCardTeam(tname, player);
    btnContainer.appendChild(tBtn);
  });

  if (badge) badge.innerText = "Все команды суммарно";
}

function selectCardTeam(teamName, player) {
  activeTeamKey = teamName;
  const badge = document.getElementById("active-team-badge");

  document.querySelectorAll(".team-toggle-btn").forEach(btn => {
    btn.classList.remove("bg-amber-500", "text-slate-950", "shadow");
    btn.classList.add("bg-slate-950", "text-slate-300");
  });

  const activeBtnId = teamName === "all" ? "btn-team-all" : "btn-team-" + teamName.replace(/\s+/g, '_');
  const activeBtn = document.getElementById(activeBtnId);
  if (activeBtn) {
    activeBtn.classList.remove("bg-slate-950", "text-slate-300");
    activeBtn.classList.add("bg-amber-500", "text-slate-950", "shadow");
  }

  if (teamName === "all") {
    if (badge) badge.innerText = "Все команды суммарно";
    const teamNames = Object.keys(player.all_teams || {});
    document.getElementById("input-team").value = teamNames.length > 1 ? teamNames[0] + " (+" + (teamNames.length - 1) + ")" : (teamNames[0] || "Команда");
    applyStatsToInputs({
      matches: player.total_matches,
      teamMatches: player.total_matches,
      goals: player.total_goals,
      assists: player.total_assists,
      yc: player.total_yellow_cards,
      rc: player.total_red_cards,
      mvp: player.total_mvp
    });
  } else {
    const tdata = player.all_teams[teamName];
    if (tdata) {
      if (badge) badge.innerText = "Только за " + teamName;
      document.getElementById("input-team").value = teamName;
      applyStatsToInputs({
        matches: tdata.matches,
        teamMatches: tdata.matches,
        goals: tdata.goals,
        assists: tdata.assists,
        yc: tdata.yellow_cards,
        rc: tdata.red_cards,
        mvp: 0
      });
    }
  }

  recalcCard();
}

// -----------------------------------------------------------------------------
// Переключатель источников (лиг)
// -----------------------------------------------------------------------------
function renderSourceFilterButtons(player) {
  const container = document.getElementById("card-source-selector");
  const btnContainer = document.getElementById("source-toggle-buttons");
  const badge = document.getElementById("active-source-badge");

  if (!container || !btnContainer) return;
  const sources = Object.entries(player.sources_data || {});
  if (sources.length <= 1) {
    container.classList.add("hidden");
    return;
  }

  container.classList.remove("hidden");
  btnContainer.innerHTML = "";

  const allBtn = document.createElement("button");
  allBtn.className = "source-toggle-btn px-3 py-1.5 rounded-xl text-xs font-black transition bg-amber-500 text-slate-950 shadow";
  allBtn.id = "btn-src-all";
  allBtn.innerHTML = "🌐 Все лиги (" + player.total_matches + "и, " + player.total_goals + "г)";
  allBtn.onclick = () => selectCardSource("all", player);
  btnContainer.appendChild(allBtn);

  sources.forEach(([sId, sData]) => {
    const sBtn = document.createElement("button");
    sBtn.className = "source-toggle-btn px-3 py-1.5 rounded-xl text-xs font-bold transition bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-700";
    sBtn.id = "btn-src-" + sId;
    sBtn.innerHTML = sData.source_name + " (" + sData.matches + "и, " + sData.goals + "г)";
    sBtn.onclick = () => selectCardSource(sId, player);
    btnContainer.appendChild(sBtn);
  });

  if (badge) badge.innerText = "Все лиги суммарно";
}

function selectCardSource(sourceKey, player) {
  activeSourceKey = sourceKey;
  const badge = document.getElementById("active-source-badge");

  document.querySelectorAll(".source-toggle-btn").forEach(btn => {
    btn.classList.remove("bg-amber-500", "text-slate-950", "shadow");
    btn.classList.add("bg-slate-950", "text-slate-300");
  });
  const activeBtn = document.getElementById("btn-src-" + sourceKey);
  if (activeBtn) {
    activeBtn.classList.remove("bg-slate-950", "text-slate-300");
    activeBtn.classList.add("bg-amber-500", "text-slate-950", "shadow");
  }

  if (sourceKey === "all") {
    if (badge) badge.innerText = "Все лиги суммарно";
    applyStatsToInputs({
      matches: player.total_matches,
      teamMatches: player.total_matches,
      goals: player.total_goals,
      assists: player.total_assists,
      yc: player.total_yellow_cards,
      rc: player.total_red_cards,
      mvp: player.total_mvp
    });
  } else {
    const sData = player.sources_data[sourceKey];
    if (sData) {
      if (badge) badge.innerText = "Только " + sData.source_name;
      applyStatsToInputs({
        matches: sData.matches,
        teamMatches: sData.matches,
        goals: sData.goals,
        assists: sData.assists,
        yc: sData.yellow_cards,
        rc: sData.red_cards,
        mvp: sData.mvp_count || 0
      });
    }
  }

  recalcCard();
}

function applyStatsToInputs(s) {
  document.getElementById("input-matches").value = s.matches;
  document.getElementById("input-team-matches").value = s.teamMatches || s.matches;
  document.getElementById("input-goals").value = s.goals;
  document.getElementById("input-assists").value = s.assists;
  document.getElementById("input-yc").value = s.yc;
  document.getElementById("input-rc").value = s.rc;
  document.getElementById("input-mvp").value = s.mvp || 0;
}

// -----------------------------------------------------------------------------
// Работа с избранным (SQLite база данных)
// -----------------------------------------------------------------------------
async function saveCurrentToFavorites() {
  const name = document.getElementById("input-name").value || "Игрок";
  const team = document.getElementById("input-team").value || "";
  const pos = document.getElementById("input-pos").value || "PIV";
  const avatar = document.getElementById("input-avatar").value || "";

  const matches = parseInt(document.getElementById("input-matches").value) || 0;
  const teamMatches = parseInt(document.getElementById("input-team-matches").value) || matches;
  const goals = parseInt(document.getElementById("input-goals").value) || 0;
  const assists = parseInt(document.getElementById("input-assists").value) || 0;
  const yc = parseInt(document.getElementById("input-yc").value) || 0;
  const rc = parseInt(document.getElementById("input-rc").value) || 0;
  const mvp = parseInt(document.getElementById("input-mvp").value) || 0;

  const payload = {
    name: name,
    team: team,
    position: pos,
    avatar: avatar,
    matches: matches,
    team_matches: teamMatches,
    goals: goals,
    assists: assists,
    yellow_cards: yc,
    red_cards: rc,
    mvp_count: mvp,
    sources_data: {
      sources: activePlayerSources || {},
      teams: activePlayerTeams || {}
    },
    notes: "Сохранено в базу: " + new Date().toLocaleDateString()
  };

  try {
    const res = await fetch(API_BASE + "/favorites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Ошибка сохранения");
    confetti({ particleCount: 70, spread: 60, origin: { y: 0.7 } });
    alert("⭐ Игрок «" + name + "» успешно сохранен в базу данных!");
    await updateFavoritesCounter();
  } catch (e) {
    alert("Не удалось сохранить игрока в базу: " + e.message);
  }
}

async function savePlayerDirectlyToFavorites(player) {
  const teamNames = Object.keys(player.all_teams || {});
  const teamName = teamNames.join(", ") || player.team || "Любительская лига";

  const payload = {
    name: player.name,
    team: teamName,
    position: "PIV",
    avatar: "",
    matches: player.total_matches,
    team_matches: player.total_matches,
    goals: player.total_goals,
    assists: player.total_assists,
    yellow_cards: player.total_yellow_cards,
    red_cards: player.total_red_cards,
    mvp_count: player.total_mvp || 0,
    sources_data: {
      sources: player.sources_data,
      teams: player.all_teams
    },
    notes: "Команды: " + teamName
  };

  try {
    const res = await fetch(API_BASE + "/favorites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      alert("⭐ «" + player.name + "» сохранен в избранное!");
      await updateFavoritesCounter();
    }
  } catch (e) {
    alert("Ошибка: " + e.message);
  }
}

async function updateFavoritesCounter() {
  const favs = await fetchWithFallback(API_BASE + "/favorites");
  const counter = document.getElementById("fav-counter");
  if (counter && favs) {
    counter.innerText = favs.length;
  }
}

async function loadFavoritesList() {
  const container = document.getElementById("favorites-list-container");
  if (!container) return;

  container.innerHTML = '<div class="col-span-3 text-center py-8 text-slate-400"><i class="fa-solid fa-spinner fa-spin text-xl text-amber-400 mb-2"></i><div>Загрузка избранных...</div></div>';

  const favs = await fetchWithFallback(API_BASE + "/favorites");
  if (!favs || favs.length === 0) {
    container.innerHTML = '<div class="col-span-3 text-center py-12 text-slate-500"><i class="fa-solid fa-star text-slate-700 text-4xl mb-3"></i><div class="text-sm font-bold">В избранном пока пусто</div><p class="text-xs text-slate-500 mt-1">Найдите игрока через поиск выше и нажмите «⭐ Сохранить в избранное»</p></div>';
    return;
  }

  container.innerHTML = "";
  favs.forEach(fav => {
    const card = document.createElement("div");
    card.className = "bg-slate-950 border border-slate-800 hover:border-amber-500/40 rounded-2xl p-4 transition flex flex-col justify-between shadow";

    card.innerHTML = '<div>' +
      '<div class="flex items-start justify-between gap-2 mb-2">' +
        '<div>' +
          '<span class="text-[10px] font-black uppercase tracking-wider text-amber-400 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">' + fav.position + '</span>' +
          '<h4 class="text-base font-black text-white mt-1">' + fav.name + '</h4>' +
          '<p class="text-xs text-slate-400">' + (fav.team || "Без команды") + '</p>' +
        '</div>' +
        '<button onclick="deleteFavoriteById(' + fav.id + ')" class="text-slate-600 hover:text-red-400 transition text-sm p-1" title="Удалить"><i class="fa-solid fa-trash"></i></button>' +
      '</div>' +
      '<div class="grid grid-cols-3 gap-2 my-3 text-center bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80 text-xs">' +
        '<div><div class="text-slate-400 text-[10px] uppercase font-bold">Матчи</div><div class="font-black text-white">' + fav.matches + '</div></div>' +
        '<div><div class="text-slate-400 text-[10px] uppercase font-bold">Голы</div><div class="font-black text-amber-400">' + fav.goals + '</div></div>' +
        '<div><div class="text-slate-400 text-[10px] uppercase font-bold">Пасы</div><div class="font-black text-sky-400">' + fav.assists + '</div></div>' +
      '</div>' +
      (fav.notes ? '<p class="text-[11px] text-slate-400 italic mb-3">«' + fav.notes + '»</p>' : '') +
    '</div>' +
    '<button onclick="restoreFavoriteToCard(' + fav.id + ')" class="w-full py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 text-xs font-black rounded-xl transition shadow active:scale-95 flex items-center justify-center gap-2"><i class="fa-solid fa-id-card"></i> Открыть карточку</button>';

    container.appendChild(card);
  });
}

async function restoreFavoriteToCard(favId) {
  const favs = await fetchWithFallback(API_BASE + "/favorites");
  const fav = (favs || []).find(f => f.id === favId);
  if (!fav) return;

  const rawSourcesData = fav.sources_data || {};
  activePlayerSources = rawSourcesData.sources || {};
  activePlayerTeams = rawSourcesData.teams || {};
  activeTeamKey = "all";
  activeSourceKey = "all";

  const restoredPlayer = {
    name: fav.name,
    team: fav.team || "",
    all_teams: activePlayerTeams,
    sources_data: activePlayerSources,
    total_matches: fav.matches,
    total_goals: fav.goals,
    total_assists: fav.assists,
    total_yellow_cards: fav.yellow_cards,
    total_red_cards: fav.red_cards,
    total_mvp: fav.mvp_count || 0
  };

  loadMergedPlayerToCard(restoredPlayer);
}

async function deleteFavoriteById(favId) {
  if (!confirm("Удалить игрока из базы избранного?")) return;
  try {
    await fetch(API_BASE + "/favorites/" + favId, { method: "DELETE" });
    await loadFavoritesList();
    await updateFavoritesCounter();
  } catch (e) {
    alert("Ошибка удаления: " + e.message);
  }
}

// -----------------------------------------------------------------------------
// Вспомогательные функции источников
// -----------------------------------------------------------------------------
async function loadSources() {
  const data = await fetchWithFallback(API_BASE + "/sources");
  if (!data) return;
  const select = document.getElementById("source-select");
  if (!select) return;
  select.innerHTML = "";
  data.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s.id;
    opt.textContent = s.name;
    select.appendChild(opt);
  });
}

async function loadSeasons(source) {
  const select = document.getElementById("season-select");
  if (!select) return;
  select.innerHTML = "<option value='all'>За все время (Суммарно)</option>";
}

async function loadPlayers(source, seasonId) {
  const playersList = document.getElementById("real-players-list");
  const loadingEl = document.getElementById("players-loading");
  const countEl = document.getElementById("players-count");

  if (loadingEl) loadingEl.classList.remove("hidden");
  if (playersList) playersList.innerHTML = "";

  const data = await fetchWithFallback(API_BASE + "/players?source=" + source + "&limit=100");

  if (loadingEl) loadingEl.classList.add("hidden");

  if (!data || !data.players) {
    if (playersList) playersList.innerHTML = '<div class="text-center text-slate-500 py-8 col-span-2">Сервер недоступен. Запустите server.py</div>';
    return;
  }

  allRealPlayers = data.players;
  if (countEl) countEl.textContent = data.count + " игроков";

  renderPlayersList(allRealPlayers);
}

function renderPlayersList(players) {
  const playersList = document.getElementById("real-players-list");
  if (!playersList) return;

  playersList.innerHTML = "";

  players.forEach((p) => {
    const card = document.createElement("div");
    card.className = "bg-slate-950 border border-slate-800 rounded-2xl p-4 flex items-center gap-4 hover:border-amber-500/40 transition cursor-pointer group";
    card.onclick = () => loadRealPlayerToCard(p);

    const ptsPerMatch = p.matches > 0 ? ((p.goals + p.assists) / p.matches).toFixed(2) : "0.00";
    const rankColor = p.rank <= 3 ? "text-amber-400" : "text-slate-400";

    card.innerHTML = '<div class="w-9 h-9 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center font-black ' + rankColor + ' text-sm shrink-0">' + p.rank + '</div>' +
      '<div class="flex-1 min-w-0">' +
        '<div class="font-bold text-white truncate group-hover:text-amber-300 transition text-sm">' + p.name + '</div>' +
        '<div class="text-xs text-slate-500 mt-0.5">' + p.matches + ' матч. · <span class="text-amber-400 font-semibold">' + p.goals + ' г</span> · <span class="text-sky-400 font-semibold">' + p.assists + ' п</span> · <span class="text-slate-400">' + ptsPerMatch + ' г+п/м</span></div>' +
      '</div>' +
      '<div class="flex gap-1.5 shrink-0">' +
        (p.yellow_cards > 0 ? '<span class="w-5 h-5 rounded bg-yellow-500/20 text-yellow-400 flex items-center justify-center text-[10px] font-bold" title="Желтые">' + p.yellow_cards + '</span>' : '') +
        (p.red_cards > 0 ? '<span class="w-5 h-5 rounded bg-red-500/20 text-red-400 flex items-center justify-center text-[10px] font-bold" title="Красные">' + p.red_cards + '</span>' : '') +
      '</div>' +
      '<button class="shrink-0 text-[11px] font-bold text-amber-400 hover:text-amber-300 border border-amber-500/30 hover:border-amber-500 rounded-lg px-2.5 py-1.5 transition">На карточку</button>';

    playersList.appendChild(card);
  });
}

function filterPlayers() {
  const q = (document.getElementById("players-search")?.value || "").toLowerCase().trim();
  if (!q) {
    renderPlayersList(allRealPlayers);
    return;
  }
  const filtered = allRealPlayers.filter(p => p.name.toLowerCase().includes(q));
  renderPlayersList(filtered);
}

function loadRealPlayerToCard(player) {
  document.getElementById("input-name").value = player.name;
  document.getElementById("input-team").value = player.source_name || "Лига";
  document.getElementById("input-matches").value = player.matches;
  document.getElementById("input-team-matches").value = player.matches;
  document.getElementById("input-goals").value = player.goals;
  document.getElementById("input-assists").value = player.assists;
  document.getElementById("input-yc").value = player.yellow_cards;
  document.getElementById("input-rc").value = player.red_cards;
  document.getElementById("input-mvp").value = player.mvp_count || 0;

  document.getElementById("card-source-selector")?.classList.add("hidden");
  document.getElementById("card-team-selector")?.classList.add("hidden");

  recalcCard();
  switchTab("player-card");

  confetti({ particleCount: 40, spread: 50, origin: { y: 0.7 } });
}

// =============================================================================
// Состояние и пресеты
// =============================================================================
const presets = {
  pivot: {
    name: "Иван Петров",
    team: "ЛФК «Зенит» Мини",
    pos: "PIV",
    matches: 14,
    teamMatches: 14,
    goals: 22,
    assists: 9,
    yc: 3,
    rc: 0,
    mvp: 5,
    flagMorning: true,
    flagFifth: false,
    flagBackpost: true,
    avatar: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>"
  },
  ala: {
    name: "Артем Воронин",
    team: "Спартак 5х5",
    pos: "ALA",
    matches: 13,
    teamMatches: 14,
    goals: 11,
    assists: 18,
    yc: 1,
    rc: 0,
    mvp: 4,
    flagMorning: true,
    flagFifth: true,
    flagBackpost: false,
    avatar: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>"
  },
  fixo: {
    name: "Сергей «Танк»",
    team: "ФК «Атлетик»",
    pos: "FIX",
    matches: 14,
    teamMatches: 14,
    goals: 5,
    assists: 7,
    yc: 8,
    rc: 1,
    mvp: 2,
    flagMorning: true,
    flagFifth: false,
    flagBackpost: false,
    avatar: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>"
  },
  goleiro: {
    name: "Михаил Смирнов",
    team: "Динамо Футзал",
    pos: "GK",
    matches: 12,
    teamMatches: 14,
    goals: 2,
    assists: 5,
    yc: 0,
    rc: 0,
    mvp: 4,
    flagMorning: false,
    flagFifth: true,
    flagBackpost: false,
    avatar: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>"
  }
};

let radarChart = null;

// Инициализация при загрузке
document.addEventListener("DOMContentLoaded", async () => {
  initRadar();
  initTiltEffect();
  recalcCard();
  updateH2H();

  const serverOk = await checkServerStatus();
  if (serverOk) {
    await updateFavoritesCounter();
    await loadSources();
    await loadSeasons(currentSource);
    await loadPlayers(currentSource, null);
  }
});

// Переключение вкладок
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => {
    el.classList.add("hidden");
    el.classList.remove("block");
    el.style.display = "none";
  });
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.remove("bg-amber-500", "text-slate-950", "shadow");
    btn.classList.add("text-slate-400");
  });

  const activeContent = document.getElementById("tab-" + tabId);
  if (activeContent) {
    activeContent.classList.remove("hidden");
    activeContent.classList.add("block");
    activeContent.style.display = "block";
  }

  const activeBtn = document.getElementById("tab-btn-" + tabId);
  if (activeBtn) {
    activeBtn.classList.add("bg-amber-500", "text-slate-950", "shadow");
    activeBtn.classList.remove("text-slate-400");
  }

  if (tabId === "player-card" && radarChart) {
    setTimeout(() => radarChart.resize(), 100);
  }

  if (tabId === "favorites") {
    loadFavoritesList();
  }
}

// Загрузка пресета
function loadPreset(key) {
  const p = presets[key];
  if (!p) return;

  document.getElementById("input-name").value = p.name;
  document.getElementById("input-team").value = p.team;
  document.getElementById("input-pos").value = p.pos;
  document.getElementById("input-matches").value = p.matches;
  document.getElementById("input-team-matches").value = p.teamMatches;
  document.getElementById("input-goals").value = p.goals;
  document.getElementById("input-assists").value = p.assists;
  document.getElementById("input-yc").value = p.yc;
  document.getElementById("input-rc").value = p.rc;
  document.getElementById("input-mvp").value = p.mvp;
  document.getElementById("flag-morning").checked = p.flagMorning;
  document.getElementById("flag-fifth").checked = p.flagFifth;
  document.getElementById("flag-backpost").checked = p.flagBackpost;
  document.getElementById("input-avatar").value = p.avatar;

  document.getElementById("card-source-selector")?.classList.add("hidden");
  document.getElementById("card-team-selector")?.classList.add("hidden");

  recalcCard();
}

// Пересчет характеристик карточки
function recalcCard() {
  const name = document.getElementById("input-name").value || "Игрок";
  const team = document.getElementById("input-team").value || "Команда";
  const pos = document.getElementById("input-pos").value;
  const avatar = document.getElementById("input-avatar").value;

  const matches = Math.max(1, parseInt(document.getElementById("input-matches").value) || 1);
  const teamMatches = Math.max(matches, parseInt(document.getElementById("input-team-matches").value) || matches);
  const goals = Math.max(0, parseInt(document.getElementById("input-goals").value) || 0);
  const assists = Math.max(0, parseInt(document.getElementById("input-assists").value) || 0);
  const yc = Math.max(0, parseInt(document.getElementById("input-yc").value) || 0);
  const rc = Math.max(0, parseInt(document.getElementById("input-rc").value) || 0);
  const mvp = Math.max(0, parseInt(document.getElementById("input-mvp").value) || 0);

  const flagMorning = document.getElementById("flag-morning").checked;
  const flagFifth = document.getElementById("flag-fifth").checked;
  const flagBackpost = document.getElementById("flag-backpost").checked;

  document.getElementById("val-matches").innerText = matches + " / " + teamMatches;
  document.getElementById("val-goals").innerText = goals;
  document.getElementById("val-assists").innerText = assists;
  document.getElementById("val-yc").innerText = yc;
  document.getElementById("val-rc").innerText = rc;
  document.getElementById("val-mvp").innerText = mvp;

  // Формулы футзальной статистики (30-99)
  const gPerMatch = goals / matches;
  let fin = Math.round(45 + Math.min(50, gPerMatch * 28) + (flagBackpost ? 4 : 0));

  const aPerMatch = assists / matches;
  let vis = Math.round(45 + Math.min(50, aPerMatch * 35));

  const ptsPerMatch = (goals + assists) / matches;
  let imp = Math.round(40 + Math.min(55, ptsPerMatch * 22) + (mvp * 2));

  const penalty = (yc * 5) + (rc * 15);
  let disc = Math.max(35, Math.round(99 - (penalty / matches * 40)));

  const attRate = matches / teamMatches;
  let att = Math.round(Math.min(99, Math.max(40, attRate * 99)));

  let clutch = Math.round(55 + Math.min(40, (mvp / matches) * 90) + (goals > 10 ? 5 : 0));

  const clamp = v => Math.min(99, Math.max(30, v));
  fin = clamp(fin);
  vis = clamp(vis);
  imp = clamp(imp);
  disc = clamp(disc);
  att = clamp(att);
  clutch = clamp(clutch);

  let ovr = 75;
  if (pos === "PIV") {
    ovr = Math.round(fin * 0.40 + imp * 0.25 + clutch * 0.15 + att * 0.10 + vis * 0.10);
  } else if (pos === "ALA") {
    ovr = Math.round(vis * 0.30 + imp * 0.25 + fin * 0.20 + att * 0.15 + clutch * 0.10);
  } else if (pos === "FIX") {
    ovr = Math.round(disc * 0.30 + att * 0.25 + imp * 0.20 + clutch * 0.15 + vis * 0.10);
  } else if (pos === "GK") {
    ovr = Math.round(clutch * 0.35 + att * 0.30 + disc * 0.20 + (flagFifth ? vis * 0.15 : 10));
  }
  ovr = clamp(ovr);

  document.getElementById("card-ovr").innerText = ovr;
  document.getElementById("card-pos").innerText = pos;
  document.getElementById("card-name").innerText = name;
  document.getElementById("card-team").innerText = team;
  document.getElementById("card-team-short").innerText = team.split(" ")[0] || "5х5";
  if (avatar) document.getElementById("card-avatar").src = avatar;

  const roleTitles = {
    PIV: "Столп (Наконечник)",
    ALA: "Бровка / Универсал",
    FIX: "Защитник (Столб)",
    GK: "Вратарь"
  };
  document.getElementById("card-role-title").innerText = roleTitles[pos] || "Игрок";

  document.getElementById("stat-fin").innerText = fin;
  document.getElementById("stat-vis").innerText = vis;
  document.getElementById("stat-imp").innerText = imp;
  document.getElementById("stat-disc").innerText = disc;
  document.getElementById("stat-att").innerText = att;
  document.getElementById("stat-clutch").innerText = clutch;

  updateBadges({
    pos: pos, goals: goals, assists: assists, matches: matches, teamMatches: teamMatches, yc: yc, rc: rc, mvp: mvp,
    flagMorning: flagMorning, flagFifth: flagFifth, flagBackpost: flagBackpost, fin: fin, vis: vis, imp: imp, disc: disc, att: att
  });

  updateRadar([fin, vis, imp, disc, att, clutch]);
  updateScoutText({ name: name, pos: pos, goals: goals, assists: assists, matches: matches, yc: yc, rc: rc, mvp: mvp, ovr: ovr, fin: fin, vis: vis, imp: imp, disc: disc, att: att, clutch: clutch, team: team });
}

function updateBadges(data) {
  const container = document.getElementById("card-badges-container");
  container.innerHTML = "";
  const badges = [];

  if (data.att >= 95 && data.flagMorning) {
    badges.push({ icon: "⏰", title: "Будильник в 9:00", bg: "bg-amber-500/20 text-amber-300 border-amber-500/40" });
  }
  if (data.flagBackpost && data.goals >= 5) {
    badges.push({ icon: "🎯", title: "Дальняя штанга", bg: "bg-rose-500/20 text-rose-300 border-rose-500/40" });
  }
  if (data.assists > data.goals && data.assists >= 6) {
    badges.push({ icon: "🧙‍♂️", title: "Альтруист", bg: "bg-purple-500/20 text-purple-300 border-purple-500/40" });
  }
  if (data.yc >= 3 || data.rc > 0) {
    badges.push({ icon: "🟨", title: "Костолом", bg: "bg-yellow-500/20 text-yellow-300 border-yellow-500/40" });
  }
  if (data.flagFifth) {
    badges.push({ icon: "👕", title: "5-й полевой", bg: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" });
  }
  if (data.imp >= 88) {
    badges.push({ icon: "👑", title: "Тащит район", bg: "bg-blue-500/20 text-blue-300 border-blue-500/40" });
  }

  if (badges.length === 0) {
    badges.push({ icon: "⚽", title: "Игрок основы", bg: "bg-slate-800 text-slate-300 border-slate-700" });
  }

  badges.forEach(b => {
    const el = document.createElement("div");
    el.className = "futsal-badge " + b.bg;
    el.innerHTML = "<span>" + b.icon + "</span> <span>" + b.title + "</span>";
    container.appendChild(el);
  });
}

function initRadar() {
  const ctx = document.getElementById("skillsRadar").getContext("2d");
  radarChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels: ["FIN (Киллер)", "VIS (Пас)", "IMP (Влияние)", "DISC (Дисципл)", "ATT (Явка)", "CLUTCH"],
      datasets: [{
        label: "Характеристики 5х5",
        data: [85, 80, 90, 70, 95, 85],
        backgroundColor: "rgba(245, 158, 11, 0.25)",
        borderColor: "#f59e0b",
        borderWidth: 2,
        pointBackgroundColor: "#fbbf24",
        pointBorderColor: "#fff"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 30,
          max: 100,
          ticks: { display: false, stepSize: 20 },
          grid: { color: "rgba(255, 255, 255, 0.1)" },
          angleLines: { color: "rgba(255, 255, 255, 0.1)" },
          pointLabels: { color: "#94a3b8", font: { size: 10, weight: "bold" } }
        }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function updateRadar(dataArray) {
  if (!radarChart) return;
  radarChart.data.datasets[0].data = dataArray;
  radarChart.update();
}

function updateScoutText(p) {
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
}

function initTiltEffect() {
  const card = document.getElementById("fut-card");
  const container = document.getElementById("fut-card-container");
  if (!card || !container) return;

  container.addEventListener("mousemove", (e) => {
    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((y - centerY) / centerY) * -12;
    const rotateY = ((x - centerX) / centerX) * 12;
    card.style.transform = "rotateX(" + rotateX + "deg) rotateY(" + rotateY + "deg)";
  });

  container.addEventListener("mouseleave", () => {
    card.style.transform = "rotateX(0deg) rotateY(0deg)";
  });
}

function exportCard() {
  const card = document.getElementById("fut-card");
  const origTransform = card.style.transform;
  card.style.transform = "none";

  html2canvas(card, {
    scale: 3,
    backgroundColor: null,
    useCORS: true
  }).then(canvas => {
    card.style.transform = origTransform;
    const link = document.createElement("a");
    link.download = "futsal-card-" + document.getElementById("card-name").innerText.toLowerCase().replace(/\s+/g, "_") + ".png";
    link.href = canvas.toDataURL("image/png");
    link.click();
    confetti({ particleCount: 70, spread: 60, origin: { y: 0.8 } });
  }).catch(err => {
    card.style.transform = origTransform;
    alert("Не удалось экспортировать картинку: " + err);
  });
}

function updateH2H() {
  const rivalKey = document.getElementById("h2h-rival-select").value;
  const rival = presets[rivalKey];
  if (!rival) return;

  document.getElementById("h2h-p2-img").src = rival.avatar;

  const p1Name = document.getElementById("input-name").value || "Иван Петров";
  const p1Fin = parseInt(document.getElementById("stat-fin").innerText) || 85;
  const p1Vis = parseInt(document.getElementById("stat-vis").innerText) || 75;
  const p1Imp = parseInt(document.getElementById("stat-imp").innerText) || 85;
  const p1Disc = parseInt(document.getElementById("stat-disc").innerText) || 70;
  const p1Att = parseInt(document.getElementById("stat-att").innerText) || 90;

  const rivalStats = {
    artem: { fin: 76, vis: 92, imp: 88, disc: 90, att: 92 },
    sergey: { fin: 60, vis: 68, imp: 72, disc: 45, att: 99 },
    mikhail: { fin: 45, vis: 75, imp: 80, disc: 95, att: 88 }
  }[rivalKey];

  const categories = [
    { label: "Киллер / Финишинг (FIN)", v1: p1Fin, v2: rivalStats.fin },
    { label: "Видение поля / Ассисты (VIS)", v1: p1Vis, v2: rivalStats.vis },
    { label: "Влияние на игру (IMP)", v1: p1Imp, v2: rivalStats.imp },
    { label: "Дисциплина (DISC)", v1: p1Disc, v2: rivalStats.disc },
    { label: "Посещаемость матчей (ATT)", v1: p1Att, v2: rivalStats.att }
  ];

  const container = document.getElementById("h2h-bars-container");
  container.innerHTML = "";

  let p1Wins = 0;
  let p2Wins = 0;

  categories.forEach(cat => {
    if (cat.v1 > cat.v2) p1Wins++;
    else if (cat.v2 > cat.v1) p2Wins++;

    const row = document.createElement("div");
    row.className = "bg-slate-950 p-3.5 rounded-xl border border-slate-800";
    row.innerHTML = '<div class="flex justify-between text-xs font-bold mb-1.5"><span class="text-amber-400">' + p1Name + ': ' + cat.v1 + '</span><span class="text-slate-400 uppercase">' + cat.label + '</span><span class="text-cyan-400">' + rival.name + ': ' + cat.v2 + '</span></div>' +
      '<div class="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden flex">' +
        '<div class="h2h-bar-p1 h-full" style="width: ' + ((cat.v1 / (cat.v1 + cat.v2)) * 100) + '%"></div>' +
        '<div class="h2h-bar-p2 h-full" style="width: ' + ((cat.v2 / (cat.v1 + cat.v2)) * 100) + '%"></div>' +
      '</div>';
    container.appendChild(row);
  });

  const verdictEl = document.getElementById("h2h-verdict");
  if (p1Wins > p2Wins) {
    verdictEl.innerHTML = "🔥 Преимущество за <b>" + p1Name + "</b> (" + p1Wins + " из " + categories.length + " категорий). Опаснее при игре в чужой штрафной!";
  } else if (p2Wins > p1Wins) {
    verdictEl.innerHTML = "⚡ Преимущество за <b>" + rival.name + "</b> (" + p2Wins + " из " + categories.length + " категорий). Лучше контролирует темп встречи!";
  } else {
    verdictEl.innerHTML = "🤝 Абсолютное равенство сил! Исход дуэли решит один эпизод на последних минутах.";
  }
}

async function onSourceChange() {
  const select = document.getElementById("source-select");
  if (!select) return;
  currentSource = select.value;
  await loadSeasons(currentSource);
  currentSeason = null;
  await loadPlayers(currentSource, null);
}

async function onSeasonChange() {
  const select = document.getElementById("season-select");
  if (!select) return;
  currentSeason = select.value || null;
  await loadPlayers(currentSource, currentSeason);
}

async function refreshPlayers() {
  await loadPlayers(currentSource, currentSeason);
}

async function checkServerStatus() {
  const dot = document.getElementById("server-status-dot");
  const text = document.getElementById("server-status-text");
  const data = await fetchWithFallback(API_BASE + "/sources");
  if (data) {
    if (dot) {
      dot.classList.remove("bg-slate-600", "animate-pulse");
      dot.classList.add("bg-emerald-500");
    }
    if (text) text.textContent = "Сервер подключён — данные с реальных сайтов лиг";
  } else {
    if (dot) {
      dot.classList.remove("bg-slate-600");
      dot.classList.add("bg-red-500", "animate-pulse");
    }
    if (text) text.textContent = "Сервер не запущен. Запустите: python server.py";
  }
  return !!data;
}



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
