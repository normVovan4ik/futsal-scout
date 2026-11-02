// =============================================================================
// Futsal Scout Hub - app.js v3.0
// Поддержка слияния аккаунтов одного игрока, переключения команд/дивизионов,
// расчета карточки FIFA 5х5 и сохранения в SQLite базу.
// =============================================================================

const API_BASE = "http://localhost:8000/api";

const DEFAULT_AVATAR = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 140 180' fill='%23d4af37'><rect width='140' height='180' fill='%23111827'/><circle cx='70' cy='55' r='28' fill='%23f59e0b'/><path d='M25 150 C25 105 50 95 70 95 C90 95 115 105 115 150 Z' fill='%23f59e0b'/><circle cx='70' cy='140' r='12' fill='%23111827'/><path d='M70 130 L70 150 M60 140 L80 140' stroke='%23f59e0b' stroke-width='2'/></svg>";

let allRealPlayers = [];
let currentSource = "liga5x5";
let currentSeason = null;

// Состояние текущего игрока на карточке
let currentActivePlayer = null;
let activePlayerSources = {};
let activePlayerTeams = {};
let activeTeamKey = "all";
let activeSourceKey = "all";

function saveCardStateToStorage() {
  try {
    const name = document.getElementById("input-name")?.value || "";
    if (!name || name === "Иван Петров") return;
    const state = {
      name: name,
      team: document.getElementById("input-team")?.value || "",
      pos: document.getElementById("input-pos")?.value || "PIV",
      avatar: document.getElementById("input-avatar")?.value || "",
      matches: document.getElementById("input-matches")?.value || 0,
      teamMatches: document.getElementById("input-team-matches")?.value || 0,
      goals: document.getElementById("input-goals")?.value || 0,
      assists: document.getElementById("input-assists")?.value || 0,
      yc: document.getElementById("input-yc")?.value || 0,
      rc: document.getElementById("input-rc")?.value || 0,
      mvp: document.getElementById("input-mvp")?.value || 0,
      currentActivePlayer: currentActivePlayer || null,
      activePlayerSources: activePlayerSources || {},
      activePlayerTeams: activePlayerTeams || {}
    };
    localStorage.setItem("futsal_card_state", JSON.stringify(state));
  } catch (e) {
    console.warn("Could not save card state:", e);
  }
}

function restoreCardStateFromStorage() {
  try {
    const raw = localStorage.getItem("futsal_card_state");
    if (!raw) return false;
    const state = JSON.parse(raw);
    if (!state || !state.name || state.name === "Иван Петров") return false;

    if (state.name) document.getElementById("input-name").value = state.name;
    if (state.team) document.getElementById("input-team").value = state.team;
    if (state.pos) document.getElementById("input-pos").value = state.pos;
    if (state.avatar) {
      document.getElementById("input-avatar").value = state.avatar;
      const avImg = document.getElementById("card-avatar");
      if (avImg) avImg.src = state.avatar;
    }
    if (state.matches !== undefined) document.getElementById("input-matches").value = state.matches;
    if (state.teamMatches !== undefined) document.getElementById("input-team-matches").value = state.teamMatches;
    if (state.goals !== undefined) document.getElementById("input-goals").value = state.goals;
    if (state.assists !== undefined) document.getElementById("input-assists").value = state.assists;
    if (state.yc !== undefined) document.getElementById("input-yc").value = state.yc;
    if (state.rc !== undefined) document.getElementById("input-rc").value = state.rc;
    if (state.mvp !== undefined) document.getElementById("input-mvp").value = state.mvp;

    currentActivePlayer = state.currentActivePlayer;
    activePlayerSources = state.activePlayerSources || {};
    activePlayerTeams = state.activePlayerTeams || {};

    if (currentActivePlayer) {
      renderTeamFilterButtons(currentActivePlayer);
      renderSourceFilterButtons(currentActivePlayer);
    }
    return true;
  } catch (e) {
    console.warn("Could not restore card state:", e);
    return false;
  }
}


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

    // Если у игрока уже есть кастомный аватар в базе или локальном хранилище, подставляем его
  const savedLocalAvatar = localStorage.getItem("futsal_avatar_" + (player.name || "").toLowerCase().trim());
  const effectiveAvatar = player.avatar || savedLocalAvatar || "";

  if (effectiveAvatar && !effectiveAvatar.startsWith("data:image/svg")) {
    document.getElementById("input-avatar").value = effectiveAvatar;
    document.getElementById("card-avatar").src = effectiveAvatar;
    player.avatar = effectiveAvatar;
  } else {
    document.getElementById("input-avatar").value = DEFAULT_AVATAR;
    document.getElementById("card-avatar").src = DEFAULT_AVATAR;
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

    const avSrc = fav.avatar || DEFAULT_AVATAR;
    card.innerHTML = '<div>' +
      '<div class="flex items-start justify-between gap-2 mb-2">' +
        '<div class="flex items-center gap-3">' +
          '<img src="' + avSrc + '" class="w-12 h-14 rounded-xl object-cover border border-amber-400/30 bg-slate-900 shadow shrink-0">' +
          '<div>' +
            '<span class="text-[10px] font-black uppercase tracking-wider text-amber-400 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">' + fav.position + '</span>' +
            '<h4 class="text-base font-black text-white mt-1">' + fav.name + '</h4>' +
            '<p class="text-xs text-slate-400">' + (fav.team || "Без команды") + '</p>' +
          '</div>' +
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
    avatar: fav.avatar || localStorage.getItem("futsal_avatar_" + (fav.name || "").toLowerCase().trim()) || "",
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
  const restored = restoreCardStateFromStorage();
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
  if (tabId === 'lineup') {
    initLineup();
  }
  if (tabId === 'head-to-head') {
    initDuelArena();
  }
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

  // Balanced stat formulas v2 (30-99)
  // FIN: goals/match  | VIS: assists/match  | IMP: (g+a)/match
  // DISC: inverse foul rate | EXP: career matches | CLUTCH: MVP rate

  const clamp = (v, lo = 30, hi = 99) => Math.min(hi, Math.max(lo, v));

  // FIN (Киллер): goals/match. 0->40 | 0.5->62 | 1->84 | 1.5->99+
  const gPerMatch = goals / matches;
  let fin = clamp(Math.round(40 + gPerMatch * 44) + (flagBackpost ? 3 : 0));

  // VIS (Плеймейкер): assists/match. 0->40 | 0.5->65 | 1->90 | 1.2->99
  const aPerMatch = assists / matches;
  let vis = clamp(Math.round(40 + aPerMatch * 50));

  // IMP (Влияние): (g+a)/match. 0->40 | 1->62 | 2->84 | 2.7->99
  const ptsPerMatch = (goals + assists) / matches;
  let imp = clamp(Math.round(40 + ptsPerMatch * 22) + (mvp >= 3 ? 3 : 0));

  // DISC (Дисциплина): inversely proportional to cards per match
  // 0 cards -> 99 | 0.5 YC/match -> ~79 | 1 YC/match -> ~59 | RC -18 penalty
  const foulRate = (yc * 10 + rc * 18) / matches;
  let disc = clamp(Math.round(99 - foulRate * 8));

  // EXP (Опыт): career match count. 5->55 | 25->72 | 60->84 | 120->93 | 200->99
  // Uses cube-root-like curve to avoid early saturation
  let exp = clamp(Math.round(40 + Math.pow(matches, 0.52) * 12));

  // THR (Угроза): dual-threat score - rewards players who BOTH score AND assist.
  // Pure scorer or pure assister get moderate rating; balanced dual-threat gets top marks.
  // 0g 0a/m -> 40 | pure 1g/m -> 68 | pure 1a/m -> 58 | balanced 0.8g+0.6a -> ~85 | elite 1.2g+0.8a -> 99
  let thr = clamp(Math.round(40 + gPerMatch * 28 + aPerMatch * 18 + Math.min(gPerMatch, aPerMatch) * 20));

  fin = clamp(fin);
  vis = clamp(vis);
  imp = clamp(imp);
  disc = clamp(disc);
  exp = clamp(exp);
  thr = clamp(thr);

  let ovr = 75;
  if (pos === "PIV") {
    ovr = Math.round(fin * 0.30 + imp * 0.25 + thr * 0.20 + vis * 0.15 + exp * 0.10);
  } else if (pos === "ALA") {
    ovr = Math.round(vis * 0.30 + imp * 0.25 + thr * 0.20 + fin * 0.15 + exp * 0.10);
  } else if (pos === "FIX") {
    ovr = Math.round(disc * 0.30 + exp * 0.20 + imp * 0.20 + thr * 0.15 + vis * 0.15);
  } else if (pos === "GK") {
    ovr = Math.round(disc * 0.35 + thr * 0.25 + exp * 0.20 + (flagFifth ? vis * 0.20 : 15));
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
  document.getElementById("stat-att").innerText = exp;
  document.getElementById("stat-clutch").innerText = thr;

  updateBadges({
    pos: pos, goals: goals, assists: assists, matches: matches, teamMatches: teamMatches, yc: yc, rc: rc, mvp: mvp,
    flagMorning: flagMorning, flagFifth: flagFifth, flagBackpost: flagBackpost, fin: fin, vis: vis, imp: imp, disc: disc, exp: exp, thr: thr
  });

  updateRadar([fin, vis, imp, disc, exp, thr]);
  updateScoutText({ name: name, pos: pos, goals: goals, assists: assists, matches: matches, yc: yc, rc: rc, mvp: mvp, ovr: ovr, fin: fin, vis: vis, imp: imp, disc: disc, exp: exp, thr: thr, team: team });
}

function updateBadges(data) {
  const container = document.getElementById("card-badges-container");
  container.innerHTML = "";
  const badges = [];

  if (data.exp >= 85 && data.flagMorning) {
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
      labels: ["FIN (Киллер)", "VIS (Плеймейкер)", "IMP (Влияние)", "DISC (Дисципл)", "EXP (Опыт)", "THR (Угроза)"],
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

  let strongPoint = p.fin >= 87 ? "Смертоносная реализация: больше гола за матч — это снайперская элита." : (p.vis >= 82 ? "Филигранное чтение игры и передачи вразрез." : (p.thr >= 82 ? "Двухсторонняя угроза: забивает и ассистирует с одинаковой эффективностью — настоящий игрок оффензивной зоны." : (p.exp >= 80 ? "Многолетняя боевая закалка — опытный ветеран лиги." : "Колоссальная самоотдача и объем беговой работы.")));
  let riskPoint = p.yc >= 3 ? "Риск перебора командных фолов (опасность 10-метровых дабл-пенальти)." : (p.disc < 65 ? "Карточки подводят: дисциплина ниже нормы, рискует оставить команду в меньшинстве." : "Иногда заигрывается и требует подстраховки при контратаках.");

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

// =============================================================================
// БИТВЫ НА ПАРКЕТЕ: 1 НА 1 (КОРОЛЬ КОРОБКИ / PANNA) И 5 НА 5 (МАТЧ ПЯТЁРОК)
// =============================================================================
let currentBattleMode = "solo"; // "solo" | "team"

let duelFighter1 = null;
let duelFighter2 = null;
let duelSearchResults1 = [];
let duelSearchResults2 = [];
let duelSearchTimeout1 = null;
let duelSearchTimeout2 = null;
let isSoloFighting = false;

// Состояние командной битвы 5х5
let currentBattleTeam1 = null;
let currentBattleTeam2 = null;
let teamSearchResults1 = [];
let teamSearchResults2 = [];
let teamSearchTimeout1 = null;
let teamSearchTimeout2 = null;
let isTeamMatchRunning = false;

// -----------------------------------------------------------------------------
// Переключение режима боя: 1 на 1 vs 5 на 5
// -----------------------------------------------------------------------------
function switchBattleMode(mode) {
  currentBattleMode = mode;
  const soloBtn = document.getElementById("battle-mode-btn-solo");
  const teamBtn = document.getElementById("battle-mode-btn-team");
  const soloSec = document.getElementById("battle-mode-solo-section");
  const teamSec = document.getElementById("battle-mode-team-section");

  if (!soloBtn || !teamBtn || !soloSec || !teamSec) return;

  if (mode === "solo") {
    soloBtn.className = "flex-1 py-3 px-4 rounded-xl text-xs sm:text-sm font-black transition-all flex items-center justify-center gap-2 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 shadow-lg shadow-amber-500/20";
    teamBtn.className = "flex-1 py-3 px-4 rounded-xl text-xs sm:text-sm font-black transition-all flex items-center justify-center gap-2 text-slate-400 hover:text-white";
    soloSec.classList.remove("hidden");
    teamSec.classList.add("hidden");
    initDuelArena();
  } else {
    teamBtn.className = "flex-1 py-3 px-4 rounded-xl text-xs sm:text-sm font-black transition-all flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 shadow-lg shadow-emerald-500/20";
    soloBtn.className = "flex-1 py-3 px-4 rounded-xl text-xs sm:text-sm font-black transition-all flex items-center justify-center gap-2 text-slate-400 hover:text-white";
    teamSec.classList.remove("hidden");
    soloSec.classList.add("hidden");
    initTeamBattleArena();
  }
}

// -----------------------------------------------------------------------------
// Расчет футзальных характеристик любого игрока (FIN, VIS, IMP, DISC, EXP, THR, OVR)
// -----------------------------------------------------------------------------
function calculateDetailedPlayerStats(p) {
  if (!p) return { fin: 50, vis: 50, imp: 50, disc: 70, exp: 50, thr: 50, ovr: 50, matches: 0, goals: 0, assists: 0, yc: 0, rc: 0, mvp: 0 };
  const matches = Math.max(1, parseInt(p.matches || p.total_matches) || 1);
  const goals = Math.max(0, parseInt(p.goals || p.total_goals) || 0);
  const assists = Math.max(0, parseInt(p.assists || p.total_assists) || 0);
  const yc = Math.max(0, parseInt(p.yellow_cards || p.total_yellow_cards || p.yc) || 0);
  const rc = Math.max(0, parseInt(p.red_cards || p.total_red_cards || p.rc) || 0);
  const mvp = Math.max(0, parseInt(p.mvp_count || p.total_mvp || p.mvp) || 0);
  const pos = p.position || p.pos || "ALA";

  const clamp = (v, lo = 30, hi = 99) => Math.min(hi, Math.max(lo, v));

  const gPerMatch = goals / matches;
  let fin = clamp(Math.round(40 + gPerMatch * 44));

  const aPerMatch = assists / matches;
  let vis = clamp(Math.round(40 + aPerMatch * 50));

  const ptsPerMatch = (goals + assists) / matches;
  let imp = clamp(Math.round(40 + ptsPerMatch * 22) + (mvp >= 3 ? 3 : 0));

  const foulRate = (yc * 10 + rc * 18) / matches;
  let disc = clamp(Math.round(99 - foulRate * 8));

  let exp = clamp(Math.round(40 + Math.pow(matches, 0.52) * 12));

  let thr = clamp(Math.round(40 + gPerMatch * 28 + aPerMatch * 18 + Math.min(gPerMatch, aPerMatch) * 20));

  let ovr = 75;
  if (pos === "PIV") {
    ovr = Math.round(fin * 0.30 + imp * 0.25 + thr * 0.20 + vis * 0.15 + exp * 0.10);
  } else if (pos === "ALA") {
    ovr = Math.round(vis * 0.30 + imp * 0.25 + thr * 0.20 + fin * 0.15 + exp * 0.10);
  } else if (pos === "FIX") {
    ovr = Math.round(disc * 0.30 + exp * 0.20 + imp * 0.20 + thr * 0.15 + vis * 0.15);
  } else if (pos === "GK") {
    ovr = Math.round(disc * 0.35 + thr * 0.25 + exp * 0.20 + 15);
  }
  ovr = clamp(ovr);

  return { fin, vis, imp, disc, exp, thr, ovr, matches, goals, assists, yc, rc, mvp };
}

function getCardPlayerObject() {
  const name = document.getElementById("input-name")?.value || "Иван Петров";
  const team = document.getElementById("input-team")?.value || "ЛФК «Зенит» Мини";
  const pos = document.getElementById("input-pos")?.value || "PIV";
  const avatar = document.getElementById("card-avatar")?.src || DEFAULT_AVATAR;
  const matches = parseInt(document.getElementById("input-matches")?.value) || 14;
  const goals = parseInt(document.getElementById("input-goals")?.value) || 22;
  const assists = parseInt(document.getElementById("input-assists")?.value) || 9;
  const yc = parseInt(document.getElementById("input-yc")?.value) || 3;
  const rc = parseInt(document.getElementById("input-rc")?.value) || 0;
  const mvp = parseInt(document.getElementById("input-mvp")?.value) || 5;

  return {
    name, team, position: pos, avatar,
    matches, goals, assists, yellow_cards: yc, red_cards: rc, mvp_count: mvp
  };
}

// =============================================================================
// РЕЖИМ 1: ОДИНОЧНАЯ ДУЭЛЬ 1 НА 1 (КОРОЛЬ КОРОБКИ / PANNA)
// =============================================================================
async function initDuelArena() {
  await populateDuelFavoritesDropdowns();

  if (!duelFighter1) {
    duelFighter1 = getCardPlayerObject();
  }
  if (!duelFighter2) {
    const p = presets.ala;
    duelFighter2 = {
      name: p.name, team: p.team, position: p.pos, avatar: p.avatar,
      matches: p.matches, goals: p.goals, assists: p.assists, yellow_cards: p.yc, red_cards: p.rc, mvp_count: p.mvp
    };
  }

  updateDuelDisplay();
  renderDuelComparisonBars();
}

async function populateDuelFavoritesDropdowns() {
  try {
    const favs = await fetchWithFallback(API_BASE + "/favorites");
    const sel1 = document.getElementById("h2h-fav-select-1");
    const sel2 = document.getElementById("h2h-fav-select-2");
    if (!sel1 || !sel2) return;

    const baseOpt = '<option value="">Из избранного...</option>';
    if (!favs || !favs.length) {
      sel1.innerHTML = baseOpt;
      sel2.innerHTML = baseOpt;
      return;
    }

    const optionsHtml = baseOpt + favs.map(f => `<option value="${f.id}">${f.name} (${f.team || 'Без команды'} · ${f.goals}г)</option>`).join("");
    sel1.innerHTML = optionsHtml;
    sel2.innerHTML = optionsHtml;
    window.cachedDuelFavorites = favs;
  } catch (e) {
    console.warn("Ошибка загрузки избранного для дуэли:", e);
  }
}

function loadCardPlayerToDuel(slot) {
  const p = getCardPlayerObject();
  if (slot === 1) duelFighter1 = p;
  else duelFighter2 = p;
  updateDuelDisplay();
  renderDuelComparisonBars();
  resetDuelFightArena();
}

function loadFavToDuel(slot, favId) {
  if (!favId || !window.cachedDuelFavorites) return;
  const fav = window.cachedDuelFavorites.find(f => String(f.id) === String(favId));
  if (!fav) return;

  const fighter = {
    name: fav.name,
    team: fav.team || "Без команды",
    position: fav.position || "ALA",
    avatar: fav.avatar || DEFAULT_AVATAR,
    matches: fav.matches || 1,
    goals: fav.goals || 0,
    assists: fav.assists || 0,
    yellow_cards: fav.yellow_cards || 0,
    red_cards: fav.red_cards || 0,
    mvp_count: fav.mvp_count || 0
  };

  if (slot === 1) duelFighter1 = fighter;
  else duelFighter2 = fighter;

  updateDuelDisplay();
  renderDuelComparisonBars();
  resetDuelFightArena();
}

function loadPresetToDuel(slot, key) {
  if (!key || !presets[key]) return;
  const p = presets[key];
  const fighter = {
    name: p.name, team: p.team, position: p.pos, avatar: p.avatar,
    matches: p.matches, goals: p.goals, assists: p.assists, yellow_cards: p.yc, red_cards: p.rc, mvp_count: p.mvp
  };

  if (slot === 1) duelFighter1 = fighter;
  else duelFighter2 = fighter;

  updateDuelDisplay();
  renderDuelComparisonBars();
  resetDuelFightArena();
}

function swapDuelPlayers() {
  if (currentBattleMode === "solo") {
    const temp = duelFighter1;
    duelFighter1 = duelFighter2;
    duelFighter2 = temp;
    updateDuelDisplay();
    renderDuelComparisonBars();
    resetDuelFightArena();
  } else {
    const tempT = currentBattleTeam1;
    currentBattleTeam1 = currentBattleTeam2;
    currentBattleTeam2 = tempT;
    updateTeamBattleDisplay();
    const arena = document.getElementById("team-match-arena");
    if (arena) arena.classList.add("hidden");
  }
}

function resetDuelArena() {
  if (currentBattleMode === "solo") {
    duelFighter1 = getCardPlayerObject();
    const p = presets.ala;
    duelFighter2 = {
      name: p.name, team: p.team, position: p.pos, avatar: p.avatar,
      matches: p.matches, goals: p.goals, assists: p.assists, yellow_cards: p.yc, red_cards: p.rc, mvp_count: p.mvp
    };
    clearDuelSearch(1);
    clearDuelSearch(2);
    updateDuelDisplay();
    renderDuelComparisonBars();
    resetDuelFightArena();
  } else {
    initTeamBattleArena();
    clearTeamBattleSearch(1);
    clearTeamBattleSearch(2);
  }
}

function resetDuelFightArena() {
  const arena = document.getElementById("duel-battle-arena");
  if (arena) arena.classList.add("hidden");
  isSoloFighting = false;
}

function handleDuelSearch(slot, query) {
  const q = (query || "").trim();
  const resContainer = document.getElementById(`h2h-search-results-${slot}`);
  if (!resContainer) return;

  if (q.length < 2) {
    resContainer.classList.add("hidden");
    resContainer.innerHTML = "";
    return;
  }

  resContainer.classList.remove("hidden");
  resContainer.innerHTML = '<div class="p-3 text-center text-slate-400"><i class="fa-solid fa-spinner fa-spin text-amber-400 mr-2"></i>Ищем во всех 3 лигах...</div>';

  const timeoutVar = slot === 1 ? duelSearchTimeout1 : duelSearchTimeout2;
  if (timeoutVar) clearTimeout(timeoutVar);

  const newTimeout = setTimeout(async () => {
    try {
      const data = await fetchWithFallback(API_BASE + "/search?q=" + encodeURIComponent(q));
      if (!data || !data.results || data.results.length === 0) {
        resContainer.innerHTML = '<div class="p-3 text-center text-slate-400 text-xs">Игрок не найден. Попробуйте фамилию.</div>';
        return;
      }

      if (slot === 1) duelSearchResults1 = data.results;
      else duelSearchResults2 = data.results;

      resContainer.innerHTML = "";
      data.results.forEach((p, idx) => {
        const item = document.createElement("div");
        item.className = "p-2.5 rounded-xl hover:bg-slate-800 cursor-pointer transition flex items-center justify-between gap-3 border border-transparent hover:border-amber-400/30";
        
        const teamsStr = Object.keys(p.all_teams || {}).slice(0, 2).join(", ") || "Команда не указана";
        const leaguesStr = (p.sources_found || []).map(s => {
          let col = "text-amber-400";
          if (s.indexOf("Старт") !== -1) col = "text-sky-400";
          if (s.indexOf("ФФГЭ") !== -1 || s.indexOf("Наградион") !== -1) col = "text-emerald-400";
          return `<span class="${col}">● ${s}</span>`;
        }).join(" ");

        item.innerHTML = `
          <div class="flex items-center gap-2.5 min-w-0 flex-1">
            <img src="${p.avatar || DEFAULT_AVATAR}" class="w-8 h-10 rounded-lg object-cover bg-slate-950 border border-slate-700 shrink-0">
            <div class="min-w-0 flex-1">
              <h5 class="font-black text-white text-xs truncate">${p.name}</h5>
              <div class="text-[10px] text-slate-400 truncate">${teamsStr}</div>
              <div class="text-[9px] text-slate-500 mt-0.5">${leaguesStr}</div>
            </div>
          </div>
          <div class="text-right shrink-0">
            <div class="text-[11px] font-black text-amber-400">${p.total_goals || 0} г</div>
            <div class="text-[10px] text-slate-400">${p.total_matches || 0} м</div>
          </div>
        `;
        item.onclick = () => selectDuelSearchResult(slot, idx);
        resContainer.appendChild(item);
      });
    } catch (e) {
      resContainer.innerHTML = '<div class="p-3 text-center text-red-400 text-xs">Ошибка поиска</div>';
    }
  }, 300);

  if (slot === 1) duelSearchTimeout1 = newTimeout;
  else duelSearchTimeout2 = newTimeout;
}

function selectDuelSearchResult(slot, index) {
  const results = slot === 1 ? duelSearchResults1 : duelSearchResults2;
  const p = results[index];
  if (!p) return;

  const teamsKeys = Object.keys(p.all_teams || {});
  const mainTeam = teamsKeys.length ? teamsKeys[0] : "Без команды";

  let pos = "ALA";
  const gPerM = (p.total_goals || 0) / Math.max(1, p.total_matches || 1);
  if (gPerM >= 0.9) pos = "PIV";
  else if ((p.total_yellow_cards || 0) >= 4) pos = "FIX";

  const fighter = {
    name: p.name,
    team: mainTeam,
    position: pos,
    avatar: p.avatar || DEFAULT_AVATAR,
    matches: p.total_matches || 1,
    goals: p.total_goals || 0,
    assists: p.total_assists || 0,
    yellow_cards: p.total_yellow_cards || 0,
    red_cards: p.total_red_cards || 0,
    mvp_count: p.total_mvp || 0
  };

  if (slot === 1) duelFighter1 = fighter;
  else duelFighter2 = fighter;

  clearDuelSearch(slot);
  updateDuelDisplay();
  renderDuelComparisonBars();
  resetDuelFightArena();
}

function clearDuelSearch(slot) {
  const inp = document.getElementById(`h2h-search-input-${slot}`);
  const res = document.getElementById(`h2h-search-results-${slot}`);
  if (inp) inp.value = "";
  if (res) {
    res.classList.add("hidden");
    res.innerHTML = "";
  }
}

function updateDuelDisplay() {
  if (!duelFighter1 || !duelFighter2) return;

  const s1 = calculateDetailedPlayerStats(duelFighter1);
  const s2 = calculateDetailedPlayerStats(duelFighter2);

  document.getElementById("h2h-p1-img").src = duelFighter1.avatar || DEFAULT_AVATAR;
  document.getElementById("h2h-p1-name").innerText = duelFighter1.name;
  document.getElementById("h2h-p1-team").innerText = duelFighter1.team || "Без команды";
  document.getElementById("h2h-p1-pos").innerText = duelFighter1.position || "PIV";
  document.getElementById("h2h-p1-ovr").innerText = s1.ovr;
  document.getElementById("h2h-p1-matches").innerText = s1.matches;
  document.getElementById("h2h-p1-goals").innerText = s1.goals;
  document.getElementById("h2h-p1-assists").innerText = s1.assists;
  document.getElementById("h2h-p1-yc").innerText = s1.yc;

  document.getElementById("h2h-p2-img").src = duelFighter2.avatar || DEFAULT_AVATAR;
  document.getElementById("h2h-p2-name").innerText = duelFighter2.name;
  document.getElementById("h2h-p2-team").innerText = duelFighter2.team || "Без команды";
  document.getElementById("h2h-p2-pos").innerText = duelFighter2.position || "ALA";
  document.getElementById("h2h-p2-ovr").innerText = s2.ovr;
  document.getElementById("h2h-p2-matches").innerText = s2.matches;
  document.getElementById("h2h-p2-goals").innerText = s2.goals;
  document.getElementById("h2h-p2-assists").innerText = s2.assists;
  document.getElementById("h2h-p2-yc").innerText = s2.yc;
}

function renderDuelComparisonBars() {
  if (!duelFighter1 || !duelFighter2) return;

  const s1 = calculateDetailedPlayerStats(duelFighter1);
  const s2 = calculateDetailedPlayerStats(duelFighter2);

  const categories = [
    { label: "Киллер / Голы (FIN)", v1: s1.fin, v2: s2.fin, desc: "Опасность и реализация в штрафной" },
    { label: "Плеймейкер / Ассисты (VIS)", v1: s1.vis, v2: s2.vis, desc: "Культура паса и видение паркета" },
    { label: "Влияние на игру (IMP)", v1: s1.imp, v2: s2.imp, desc: "Суммарный атакующий вклад (Г+П)" },
    { label: "Дисциплина (DISC)", v1: s1.disc, v2: s2.disc, desc: "Чистота отбора без фолов и карточек" },
    { label: "Опыт и карьера (EXP)", v1: s1.exp, v2: s2.exp, desc: "Наигранные матчи в лигах" },
    { label: "Двусторонняя угроза (THR)", v1: s1.thr, v2: s2.thr, desc: "Умение одновременно и забивать, и отдавать" },
    { label: "Общий рейтинг (OVR)", v1: s1.ovr, v2: s2.ovr, desc: "Интегральный уровень игрока 5х5" }
  ];

  const container = document.getElementById("h2h-bars-container");
  if (!container) return;
  container.innerHTML = "";

  let p1Wins = 0;
  let p2Wins = 0;

  categories.forEach(cat => {
    let winnerBadge = "";
    if (cat.v1 > cat.v2) {
      p1Wins++;
      winnerBadge = `<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/40">+${cat.v1 - cat.v2} Золотой</span>`;
    } else if (cat.v2 > cat.v1) {
      p2Wins++;
      winnerBadge = `<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">+${cat.v2 - cat.v1} Циановый</span>`;
    } else {
      winnerBadge = `<span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-800 text-slate-400">Ничья</span>`;
    }

    const total = Math.max(1, cat.v1 + cat.v2);
    const p1Pct = Math.round((cat.v1 / total) * 100);
    const p2Pct = 100 - p1Pct;

    const row = document.createElement("div");
    row.className = "bg-slate-900/80 p-3.5 rounded-2xl border border-slate-800/80 transition hover:border-slate-700";
    row.innerHTML = `
      <div class="flex items-center justify-between text-xs font-bold mb-1.5 flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <span class="text-amber-400 font-black text-sm">${cat.v1}</span>
          <span class="text-slate-300 font-semibold">${duelFighter1.name.split(' ')[0]}</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-slate-300 font-extrabold uppercase text-[11px] tracking-wider">${cat.label}</span>
          ${winnerBadge}
        </div>
        <div class="flex items-center gap-2">
          <span class="text-slate-300 font-semibold">${duelFighter2.name.split(' ')[0]}</span>
          <span class="text-cyan-400 font-black text-sm">${cat.v2}</span>
        </div>
      </div>
      <div class="w-full bg-slate-950 h-3 rounded-full overflow-hidden flex border border-slate-800 p-0.5">
        <div class="h-full rounded-full transition-all duration-500 ${cat.v1 >= cat.v2 ? 'bg-gradient-to-r from-amber-500 to-amber-400' : 'bg-amber-500/50'}" style="width: ${p1Pct}%"></div>
        <div class="h-full rounded-full transition-all duration-500 ml-0.5 ${cat.v2 >= cat.v1 ? 'bg-gradient-to-r from-cyan-400 to-cyan-500' : 'bg-cyan-500/50'}" style="width: ${p2Pct}%"></div>
      </div>
      <div class="text-[10px] text-slate-500 mt-1 italic">${cat.desc}</div>
    `;
    container.appendChild(row);
  });

  const verdictEl = document.getElementById("h2h-verdict");
  if (verdictEl) {
    if (p1Wins > p2Wins) {
      verdictEl.innerHTML = `🔥 По сумме качеств лидирует <b>${duelFighter1.name}</b> (выиграл <b>${p1Wins} из ${categories.length}</b> категорий). Значительно опаснее в атаке!`;
    } else if (p2Wins > p1Wins) {
      verdictEl.innerHTML = `⚡ По сумме качеств сильнее <b>${duelFighter2.name}</b> (выиграл <b>${p2Wins} из ${categories.length}</b> категорий). Строже играет по позиции!`;
    } else {
      verdictEl.innerHTML = `🤝 <b>Идеальный баланс сил!</b> Игроки абсолютно равны (по ${p1Wins} побед).`;
    }
  }
}

// -----------------------------------------------------------------------------
// 🔥 1 НА 1: ПАННА-ДУЭЛЬ («КОРОЛЬ КОРОБКИ») С ВОЗМОЖНОСТЬЮ МГНОВЕННОГО НОКАУТА
// -----------------------------------------------------------------------------
async function startSoloPannaFight() {
  if (isSoloFighting || !duelFighter1 || !duelFighter2) return;
  isSoloFighting = true;

  const arena = document.getElementById("duel-battle-arena");
  const roundsContainer = document.getElementById("duel-rounds-container");
  const ceremony = document.getElementById("duel-winner-ceremony");
  const scoreP1El = document.getElementById("duel-score-p1");
  const scoreP2El = document.getElementById("duel-score-p2");
  const scoreP1Name = document.getElementById("duel-score-p1-name");
  const scoreP2Name = document.getElementById("duel-score-p2-name");
  const liveTitle = document.getElementById("duel-live-title");

  if (!arena || !roundsContainer) return;

  arena.classList.remove("hidden");
  ceremony.classList.add("hidden");
  roundsContainer.innerHTML = "";
  scoreP1El.innerText = "0";
  scoreP2El.innerText = "0";
  scoreP1Name.innerText = duelFighter1.name.split(' ')[0];
  scoreP2Name.innerText = duelFighter2.name.split(' ')[0];
  liveTitle.innerText = `Панна-битва: ${duelFighter1.name} vs ${duelFighter2.name}`;

  arena.scrollIntoView({ behavior: "smooth", block: "center" });

  const s1 = calculateDetailedPlayerStats(duelFighter1);
  const s2 = calculateDetailedPlayerStats(duelFighter2);

  const roundsConfig = [
    {
      num: 1,
      name: "👟 Проброс между ног (Панна-попытка)",
      icon: "fa-socks",
      base1: Math.round((s1.vis + s1.thr) / 2),
      base2: Math.round((s2.vis + s2.thr) / 2),
      isPannaRound: true,
      descP1Win: `${duelFighter1.name} раскачивает подошвой, ловит защитника на широком шаге и пробрасывает точно между ног! Чистый футзальный стиль.`,
      descP2Win: `${duelFighter2.name} молниеносно делает эластико и пускает мяч в «домик»! Трибуны ревут от восторга.`,
      descDraw: `Плотная стойка на полусогнутых — ни один не позволил пустить мяч себе между ног.`
    },
    {
      num: 2,
      name: "🎯 Удар с носка в микро-ворота",
      icon: "fa-bullseye",
      base1: s1.fin,
      base2: s2.fin,
      isPannaRound: false,
      descP1Win: `${duelFighter1.name} на замахе убирает под рабочую ногу и филигранно шьёт с пыра в самый угол микро-ворот!`,
      descP2Win: `${duelFighter2.name} без раздумий вколачивает с разворота низом рикошетом от штанги!`,
      descDraw: `Оба удара сотрясают штанги микро-ворот — ничья по очкам.`
    },
    {
      num: 3,
      name: "🧱 Качели на подошве и игра корпусом у сетки",
      icon: "fa-shield-halved",
      base1: Math.round(s1.thr * 0.6 + s1.disc * 0.4),
      base2: Math.round(s2.thr * 0.6 + s2.disc * 0.4),
      isPannaRound: false,
      descP1Win: `${duelFighter1.name} прижимает мяч подошвой к паркету, ставит мощный корпус и выбивает победное очко!`,
      descP2Win: `${duelFighter2.name} на запредельном балансе обкрадывает оппонента у сетки коробки и закатывает в пустые!`,
      descDraw: `Жесточайшая борьба плечо в плечо у ограждения клетки — время раунда истекло.`
    }
  ];

  let p1Score = 0;
  let p2Score = 0;
  let instantKnockout = false;
  let knockoutWinner = 0;

  for (let i = 0; i < roundsConfig.length; i++) {
    await new Promise(r => setTimeout(r, 700));

    const r = roundsConfig[i];
    const roll1 = Math.floor(Math.random() * 15) - 7;
    const roll2 = Math.floor(Math.random() * 15) - 7;
    const total1 = Math.max(15, r.base1 + roll1);
    const total2 = Math.max(15, r.base2 + roll2);

    let roundWinner = 0;
    let roundText = r.descDraw;
    let badgeHtml = '<span class="px-2 py-0.5 rounded text-[10px] font-black bg-slate-800 text-slate-400">Ничья</span>';

    const diff = Math.abs(total1 - total2);

    if (total1 > total2) {
      roundWinner = 1;
      p1Score++;
      roundText = r.descP1Win;
      badgeHtml = `<span class="px-2 py-0.5 rounded text-[10px] font-black bg-amber-500/20 text-amber-300 border border-amber-500/40">+${diff} за ${duelFighter1.name.split(' ')[0]}</span>`;
      
      // Проверка на мгновенный нокаут панны
      if (r.isPannaRound && diff >= 12) {
        instantKnockout = true;
        knockoutWinner = 1;
        p1Score = 3;
        badgeHtml = `<span class="px-2.5 py-0.5 rounded text-[10px] font-black bg-rose-500 text-white animate-pulse">💥 PANNA KNOCKOUT!</span>`;
        roundText = `💥 ПА-А-АННА! ${duelFighter1.name} совершает невозможное: идеальный проброс между ног с полным контролем мяча! МГНОВЕННЫЙ НОКАУТ!`;
      }
    } else if (total2 > total1) {
      roundWinner = 2;
      p2Score++;
      roundText = r.descP2Win;
      badgeHtml = `<span class="px-2 py-0.5 rounded text-[10px] font-black bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">+${diff} за ${duelFighter2.name.split(' ')[0]}</span>`;
      
      if (r.isPannaRound && diff >= 12) {
        instantKnockout = true;
        knockoutWinner = 2;
        p2Score = 3;
        badgeHtml = `<span class="px-2.5 py-0.5 rounded text-[10px] font-black bg-rose-500 text-white animate-pulse">💥 PANNA KNOCKOUT!</span>`;
        roundText = `💥 ПА-А-АННА! ${duelFighter2.name} поймал соперника на противоходе и элегантно пустил мяч в домик! МГНОВЕННЫЙ НОКАУТ В ПЕРВОМ РАУНДЕ!`;
      }
    }

    scoreP1El.innerText = p1Score;
    scoreP2El.innerText = p2Score;

    const roundEl = document.createElement("div");
    roundEl.className = "duel-round-card bg-slate-900/90 border " + (roundWinner === 1 ? 'border-amber-500/50' : (roundWinner === 2 ? 'border-cyan-500/50' : 'border-slate-800')) + " p-3.5 rounded-2xl";
    roundEl.innerHTML = `
      <div class="flex items-center justify-between text-xs font-bold mb-1">
        <span class="text-white flex items-center gap-1.5"><i class="fa-solid ${r.icon} text-amber-400"></i> Раунд ${r.num}: ${r.name}</span>
        ${badgeHtml}
      </div>
      <div class="flex items-center justify-between text-[11px] text-slate-400 mb-2">
        <span class="${roundWinner === 1 ? 'text-amber-300 font-black' : ''}">${duelFighter1.name.split(' ')[0]}: ${total1}</span>
        <span class="${roundWinner === 2 ? 'text-cyan-300 font-black' : ''}">${duelFighter2.name.split(' ')[0]}: ${total2}</span>
      </div>
      <p class="text-xs text-slate-200 italic bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/80">«${roundText}»</p>
    `;
    roundsContainer.appendChild(roundEl);

    if (instantKnockout) break;
  }

  await new Promise(r => setTimeout(r, 600));

  ceremony.classList.remove("hidden");
  ceremony.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const streetPenalties = [
    "Проигравший покупает 2 бутылки колы и собирает мячи после тренировки!",
    "Проигравший встаёт в ворота на следующей игре и ловит пушечные удары с 6 метров!",
    "Победитель объявляется официальным Королём Коробки с пожизненным респектом во дворе!",
    "Проигравший делает 20 отжиманий прямо на паркете под одобрительный гул команды!"
  ];
  const pText = streetPenalties[Math.floor(Math.random() * streetPenalties.length)];

  if (p1Score > p2Score) {
    ceremony.innerHTML = `
      <div class="text-4xl mb-2">👑🏆</div>
      <h4 class="text-xl font-black text-amber-400 mb-1">КОРОЛЬ КОРОБКИ: ${duelFighter1.name.toUpperCase()}!</h4>
      <p class="text-xs font-bold text-white mb-3">${instantKnockout ? '⚡ ПОБЕДА ЧИСТЫМ PANNA-НОКАУТОМ!' : `Счёт по раундам: <span class="text-amber-400 text-lg">${p1Score}</span> : <span class="text-cyan-400 text-lg">${p2Score}</span>`}</p>
      <div class="inline-block p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs font-semibold mb-4 max-w-lg">
        👟 <b>Уличный приговор:</b> ${pText}
      </div>
      <div>
        <button onclick="startSoloPannaFight()" class="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs uppercase tracking-wider transition shadow">
          <i class="fa-solid fa-rotate-right mr-1"></i> Реванш на коробке
        </button>
      </div>
    `;
  } else if (p2Score > p1Score) {
    ceremony.innerHTML = `
      <div class="text-4xl mb-2">👑🏆</div>
      <h4 class="text-xl font-black text-cyan-400 mb-1">КОРОЛЬ КОРОБКИ: ${duelFighter2.name.toUpperCase()}!</h4>
      <p class="text-xs font-bold text-white mb-3">${instantKnockout ? '⚡ ПОБЕДА ЧИСТЫМ PANNA-НОКАУТОМ!' : `Счёт по раундам: <span class="text-amber-400 text-lg">${p1Score}</span> : <span class="text-cyan-400 text-lg">${p2Score}</span>`}</p>
      <div class="inline-block p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-200 text-xs font-semibold mb-4 max-w-lg">
        👟 <b>Уличный приговор:</b> ${pText}
      </div>
      <div>
        <button onclick="startSoloPannaFight()" class="px-5 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-black text-xs uppercase tracking-wider transition shadow">
          <i class="fa-solid fa-rotate-right mr-1"></i> Реванш на коробке
        </button>
      </div>
    `;
  } else {
    ceremony.innerHTML = `
      <div class="text-4xl mb-2">🤝⚽</div>
      <h4 class="text-xl font-black text-white mb-1">НИЧЬЯ НА КОРОБКЕ: ${p1Score} : ${p2Score}!</h4>
      <p class="text-xs text-slate-400 mb-3">Оба дриблера сохранили честь коробки. Никто не уступил ни сантиметра.</p>
      <div>
        <button onclick="startSoloPannaFight()" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-cyan-500 text-slate-950 font-black text-xs uppercase tracking-wider transition shadow">
          <i class="fa-solid fa-rotate-right mr-1"></i> Золотой гол (Реванш)
        </button>
      </div>
    `;
  }

  isSoloFighting = false;
}

// Псевдоним старого метода
function startDuelFight() {
  startSoloPannaFight();
}


// =============================================================================
// РЕЖИМ 2: КОМАНДНАЯ БИТВА 5 НА 5 (МАТЧ ДВУХ ПЯТЁРОК)
// =============================================================================

const PRESET_TEAMS = {
  zenit: {
    name: "ЛФК «Зенит» Мини",
    league: "Лига 5х5 (Екатеринбург)",
    badge: "⚡",
    players: [
      { name: "Иван Петров", position: "PIV", goals: 22, assists: 9, matches: 14, yellow_cards: 3, avatar: DEFAULT_AVATAR },
      { name: "Артем Воронин", position: "ALA", goals: 11, assists: 18, matches: 13, yellow_cards: 1, avatar: DEFAULT_AVATAR },
      { name: "Дмитрий Быстров", position: "ALA", goals: 9, assists: 12, matches: 12, yellow_cards: 2, avatar: DEFAULT_AVATAR },
      { name: "Сергей «Танк»", position: "FIX", goals: 5, assists: 7, matches: 14, yellow_cards: 8, avatar: DEFAULT_AVATAR },
      { name: "Михаил Смирнов", position: "GK", goals: 2, assists: 5, matches: 12, yellow_cards: 0, avatar: DEFAULT_AVATAR }
    ]
  },
  polynom: {
    name: "Полином Екатеринбург",
    league: "Лига Старт (Екатеринбург)",
    badge: "📐",
    players: [
      { name: "Владимир Ершов", position: "PIV", goals: 25, assists: 12, matches: 15, yellow_cards: 2, avatar: DEFAULT_AVATAR },
      { name: "Алексей Кузнецов", position: "ALA", goals: 14, assists: 10, matches: 14, yellow_cards: 3, avatar: DEFAULT_AVATAR },
      { name: "Кирилл Морозов", position: "ALA", goals: 8, assists: 14, matches: 13, yellow_cards: 1, avatar: DEFAULT_AVATAR },
      { name: "Роман Степанов", position: "FIX", goals: 4, assists: 6, matches: 15, yellow_cards: 5, avatar: DEFAULT_AVATAR },
      { name: "Евгений Белов", position: "GK", goals: 0, assists: 3, matches: 15, yellow_cards: 0, avatar: DEFAULT_AVATAR }
    ]
  },
  solyanka: {
    name: "Солянка 5х5",
    league: "Лига 5х5 (Екатеринбург)",
    badge: "🍲",
    players: [
      { name: "Максим Громов", position: "PIV", goals: 18, assists: 8, matches: 12, yellow_cards: 1, avatar: DEFAULT_AVATAR },
      { name: "Илья Волков", position: "ALA", goals: 10, assists: 11, matches: 11, yellow_cards: 4, avatar: DEFAULT_AVATAR },
      { name: "Павел Соколов", position: "ALA", goals: 7, assists: 9, matches: 12, yellow_cards: 2, avatar: DEFAULT_AVATAR },
      { name: "Антон Захаров", position: "FIX", goals: 3, assists: 5, matches: 12, yellow_cards: 6, avatar: DEFAULT_AVATAR },
      { name: "Денис Орлов", position: "GK", goals: 1, assists: 2, matches: 12, yellow_cards: 1, avatar: DEFAULT_AVATAR }
    ]
  },
  athletic: {
    name: "ФК «Атлетик»",
    league: "Лига Старт (Екатеринбург)",
    badge: "🛡️",
    players: [
      { name: "Николай Котов", position: "PIV", goals: 16, assists: 7, matches: 13, yellow_cards: 2, avatar: DEFAULT_AVATAR },
      { name: "Егор Васильев", position: "ALA", goals: 12, assists: 10, matches: 13, yellow_cards: 2, avatar: DEFAULT_AVATAR },
      { name: "Тимур Алиев", position: "ALA", goals: 8, assists: 13, matches: 12, yellow_cards: 1, avatar: DEFAULT_AVATAR },
      { name: "Виктор Сухов", position: "FIX", goals: 5, assists: 4, matches: 14, yellow_cards: 7, avatar: DEFAULT_AVATAR },
      { name: "Олег Медведев", position: "GK", goals: 0, assists: 4, matches: 13, yellow_cards: 0, avatar: DEFAULT_AVATAR }
    ]
  },
  spartak: {
    name: "Спартак 5х5",
    league: "Лига 5х5 (Екатеринбург)",
    badge: "🔴",
    players: [
      { name: "Владислав Попов", position: "PIV", goals: 20, assists: 11, matches: 14, yellow_cards: 3, avatar: DEFAULT_AVATAR },
      { name: "Данил Ковалев", position: "ALA", goals: 13, assists: 15, matches: 14, yellow_cards: 2, avatar: DEFAULT_AVATAR },
      { name: "Артур Сафин", position: "ALA", goals: 9, assists: 11, matches: 13, yellow_cards: 1, avatar: DEFAULT_AVATAR },
      { name: "Глеб Новиков", position: "FIX", goals: 4, assists: 5, matches: 14, yellow_cards: 5, avatar: DEFAULT_AVATAR },
      { name: "Валерий Чернов", position: "GK", goals: 1, assists: 3, matches: 14, yellow_cards: 0, avatar: DEFAULT_AVATAR }
    ]
  },
  dinamo: {
    name: "Динамо Футзал",
    league: "ФФГЭ (Наградион)",
    badge: "👮",
    players: [
      { name: "Станислав Жуков", position: "PIV", goals: 19, assists: 6, matches: 12, yellow_cards: 1, avatar: DEFAULT_AVATAR },
      { name: "Юрий Сидоров", position: "ALA", goals: 11, assists: 12, matches: 12, yellow_cards: 3, avatar: DEFAULT_AVATAR },
      { name: "Матвей Федоров", position: "ALA", goals: 7, assists: 10, matches: 11, yellow_cards: 0, avatar: DEFAULT_AVATAR },
      { name: "Константин Павлов", position: "FIX", goals: 3, assists: 4, matches: 12, yellow_cards: 4, avatar: DEFAULT_AVATAR },
      { name: "Игорь Макаров", position: "GK", goals: 0, assists: 2, matches: 12, yellow_cards: 0, avatar: DEFAULT_AVATAR }
    ]
  }
};

function initTeamBattleArena() {
  if (!currentBattleTeam1) {
    currentBattleTeam1 = JSON.parse(JSON.stringify(PRESET_TEAMS.zenit));
  }
  if (!currentBattleTeam2) {
    currentBattleTeam2 = JSON.parse(JSON.stringify(PRESET_TEAMS.athletic));
  }
  updateTeamBattleDisplay();
}

function loadMyLineupToTeamBattle(slot) {
  // Загружаем текущий состав пятёрки из вкладки 5х5
  const activeLineup = currentLineup.filter(Boolean);
  let squad = [];

  if (activeLineup.length >= 5) {
    squad = activeLineup.slice(0, 5).map(p => ({
      name: p.name,
      position: p.position || "ALA",
      goals: p.goals || 0,
      assists: p.assists || 0,
      matches: p.matches || 1,
      yellow_cards: p.yellow_cards || 0,
      avatar: p.avatar || DEFAULT_AVATAR
    }));
  } else {
    // Дополняем игроками из избранного или пресета
    const baseP = getCardPlayerObject();
    squad.push(baseP);
    const presetsList = [presets.ala, presets.fixo, presets.goleiro, presets.pivot];
    for (let i = 0; i < 4; i++) {
      const pr = presetsList[i];
      squad.push({
        name: pr.name, position: pr.pos, goals: pr.goals, assists: pr.assists, matches: pr.matches, yellow_cards: pr.yc, avatar: pr.avatar
      });
    }
  }

  const teamObj = {
    name: "Моя Тактическая Пятёрка",
    league: "Сборная турнира",
    badge: "⭐",
    players: squad
  };

  if (slot === 1) currentBattleTeam1 = teamObj;
  else currentBattleTeam2 = teamObj;

  updateTeamBattleDisplay();
  const arena = document.getElementById("team-match-arena");
  if (arena) arena.classList.add("hidden");
}

function loadPresetTeamToBattle(slot, key) {
  if (!key || !PRESET_TEAMS[key]) return;
  const teamObj = JSON.parse(JSON.stringify(PRESET_TEAMS[key]));
  if (slot === 1) currentBattleTeam1 = teamObj;
  else currentBattleTeam2 = teamObj;
  updateTeamBattleDisplay();
  const arena = document.getElementById("team-match-arena");
  if (arena) arena.classList.add("hidden");
}

function handleTeamBattleSearch(slot, query) {
  const q = (query || "").trim();
  const resContainer = document.getElementById(`team-search-results-${slot}`);
  if (!resContainer) return;

  if (q.length < 2) {
    resContainer.classList.add("hidden");
    resContainer.innerHTML = "";
    return;
  }

  resContainer.classList.remove("hidden");
  resContainer.innerHTML = '<div class="p-3 text-center text-slate-400"><i class="fa-solid fa-spinner fa-spin text-emerald-400 mr-2"></i>Ищем команды в 3 лигах...</div>';

  const timeoutVar = slot === 1 ? teamSearchTimeout1 : teamSearchTimeout2;
  if (timeoutVar) clearTimeout(timeoutVar);

  const newTimeout = setTimeout(async () => {
    try {
      const data = await fetchWithFallback(API_BASE + "/teams/search?q=" + encodeURIComponent(q));
      if (!data || !data.results || data.results.length === 0) {
        resContainer.innerHTML = '<div class="p-3 text-center text-slate-400 text-xs">Команда не найдена</div>';
        return;
      }

      if (slot === 1) teamSearchResults1 = data.results;
      else teamSearchResults2 = data.results;

      resContainer.innerHTML = "";
      data.results.forEach((t, idx) => {
        const item = document.createElement("div");
        item.className = "p-2.5 rounded-xl hover:bg-slate-800 cursor-pointer transition flex items-center justify-between gap-3 border border-transparent hover:border-emerald-400/30";
        item.innerHTML = `
          <div>
            <h5 class="font-black text-white text-xs truncate">👕 ${t.team_name}</h5>
            <div class="text-[10px] text-slate-400 mt-0.5">${t.source_name} · ${t.tournament_name || 'Чемпионат'}</div>
          </div>
          <div class="text-right text-[11px] font-bold text-amber-400">${t.matches || 0} матчей</div>
        `;
        item.onclick = () => selectTeamBattleSearchResult(slot, idx);
        resContainer.appendChild(item);
      });
    } catch (e) {
      resContainer.innerHTML = '<div class="p-3 text-center text-red-400 text-xs">Ошибка поиска</div>';
    }
  }, 300);

  if (slot === 1) teamSearchTimeout1 = newTimeout;
  else teamSearchTimeout2 = newTimeout;
}

function selectTeamBattleSearchResult(slot, index) {
  const results = slot === 1 ? teamSearchResults1 : teamSearchResults2;
  const t = results[index];
  if (!t) return;

  // Генерируем сбалансированную футзальную пятерку для найденной команды
  const baseName = t.team_name;
  const squad = [
    { name: `Форвард (${baseName})`, position: "PIV", goals: 18, assists: 6, matches: t.matches || 12, yellow_cards: 2, avatar: DEFAULT_AVATAR },
    { name: `Вингер 1 (${baseName})`, position: "ALA", goals: 10, assists: 14, matches: t.matches || 12, yellow_cards: 1, avatar: DEFAULT_AVATAR },
    { name: `Вингер 2 (${baseName})`, position: "ALA", goals: 8, assists: 10, matches: t.matches || 12, yellow_cards: 3, avatar: DEFAULT_AVATAR },
    { name: `Защитник (${baseName})`, position: "FIX", goals: 4, assists: 5, matches: t.matches || 12, yellow_cards: 5, avatar: DEFAULT_AVATAR },
    { name: `Вратарь (${baseName})`, position: "GK", goals: 0, assists: 3, matches: t.matches || 12, yellow_cards: 0, avatar: DEFAULT_AVATAR }
  ];

  const teamObj = {
    name: t.team_name,
    league: t.source_name,
    badge: "👕",
    players: squad
  };

  if (slot === 1) currentBattleTeam1 = teamObj;
  else currentBattleTeam2 = teamObj;

  clearTeamBattleSearch(slot);
  updateTeamBattleDisplay();
  const arena = document.getElementById("team-match-arena");
  if (arena) arena.classList.add("hidden");
}

function clearTeamBattleSearch(slot) {
  const inp = document.getElementById(`team-search-input-${slot}`);
  const res = document.getElementById(`team-search-results-${slot}`);
  if (inp) inp.value = "";
  if (res) {
    res.classList.add("hidden");
    res.innerHTML = "";
  }
}

function calculateTeamRatings(team) {
  if (!team || !team.players || !team.players.length) {
    return { ovr: 80, att: 80, def: 80, gk: 80, pass: 80, exp: 80 };
  }
  let sumOvr = 0, sumAtt = 0, sumDef = 0, sumPass = 0, sumExp = 0;
  let gkRating = 82;

  team.players.forEach(p => {
    const s = calculateDetailedPlayerStats(p);
    sumOvr += s.ovr;
    sumAtt += Math.round(s.fin * 0.6 + s.thr * 0.4);
    sumDef += Math.round(s.disc * 0.5 + s.exp * 0.3 + 20);
    sumPass += s.vis;
    sumExp += s.exp;
    if (p.position === "GK") {
      gkRating = Math.round(s.disc * 0.35 + s.exp * 0.35 + 25);
    }
  });

  const len = team.players.length;
  return {
    ovr: Math.round(sumOvr / len),
    att: Math.round(sumAtt / len),
    def: Math.round(sumDef / len),
    pass: Math.round(sumPass / len),
    exp: Math.round(sumExp / len),
    gk: gkRating
  };
}

function updateTeamBattleDisplay() {
  if (!currentBattleTeam1 || !currentBattleTeam2) return;

  const r1 = calculateTeamRatings(currentBattleTeam1);
  const r2 = calculateTeamRatings(currentBattleTeam2);

  // Команда 1
  document.getElementById("team-1-name").innerText = currentBattleTeam1.name;
  document.getElementById("team-1-league").innerText = currentBattleTeam1.league || "Лига 5х5";
  document.getElementById("team-1-badge").innerText = currentBattleTeam1.badge || "⚽";
  document.getElementById("team-1-ovr").innerText = r1.ovr;
  document.getElementById("team-1-att-rating").innerText = r1.att;
  document.getElementById("team-1-def-rating").innerText = r1.def;
  document.getElementById("team-1-gk-rating").innerText = r1.gk;

  const roster1El = document.getElementById("team-1-roster-preview");
  roster1El.innerHTML = currentBattleTeam1.players.map(p => `
    <div class="bg-slate-950 p-1.5 rounded-xl border border-slate-800">
      <img src="${p.avatar || DEFAULT_AVATAR}" class="w-8 h-9 rounded-lg object-cover mx-auto bg-slate-900 border border-amber-400/30">
      <div class="text-[9px] font-black text-amber-400 mt-1 uppercase">${p.position}</div>
      <div class="text-[9px] text-white truncate max-w-[50px] mx-auto font-bold">${p.name.split(' ')[0]}</div>
    </div>
  `).join("");

  // Команда 2
  document.getElementById("team-2-name").innerText = currentBattleTeam2.name;
  document.getElementById("team-2-league").innerText = currentBattleTeam2.league || "Лига Старт";
  document.getElementById("team-2-badge").innerText = currentBattleTeam2.badge || "🛡️";
  document.getElementById("team-2-ovr").innerText = r2.ovr;
  document.getElementById("team-2-att-rating").innerText = r2.att;
  document.getElementById("team-2-def-rating").innerText = r2.def;
  document.getElementById("team-2-gk-rating").innerText = r2.gk;

  const roster2El = document.getElementById("team-2-roster-preview");
  roster2El.innerHTML = currentBattleTeam2.players.map(p => `
    <div class="bg-slate-950 p-1.5 rounded-xl border border-slate-800">
      <img src="${p.avatar || DEFAULT_AVATAR}" class="w-8 h-9 rounded-lg object-cover mx-auto bg-slate-900 border border-cyan-400/30">
      <div class="text-[9px] font-black text-cyan-400 mt-1 uppercase">${p.position}</div>
      <div class="text-[9px] text-white truncate max-w-[50px] mx-auto font-bold">${p.name.split(' ')[0]}</div>
    </div>
  `).join("");

  renderTeamComparisonBars(r1, r2);
}

function renderTeamComparisonBars(r1, r2) {
  const categories = [
    { label: "Атакующая мощь (Attack)", v1: r1.att, v2: r2.att },
    { label: "Контроль мяча и пас (Passing)", v1: r1.pass, v2: r2.pass },
    { label: "Оборонительный цемент (Defense)", v1: r1.def, v2: r2.def },
    { label: "Фактор голкипера (Goalkeeper)", v1: r1.gk, v2: r2.gk },
    { label: "Опыт и сыгранность (Experience)", v1: r1.exp, v2: r2.exp }
  ];

  const container = document.getElementById("team-bars-container");
  if (!container) return;
  container.innerHTML = "";

  categories.forEach(cat => {
    const total = Math.max(1, cat.v1 + cat.v2);
    const p1Pct = Math.round((cat.v1 / total) * 100);
    const p2Pct = 100 - p1Pct;

    const row = document.createElement("div");
    row.className = "bg-slate-900/80 p-3 rounded-2xl border border-slate-800";
    row.innerHTML = `
      <div class="flex items-center justify-between text-xs font-bold mb-1">
        <span class="text-amber-400">${cat.v1}</span>
        <span class="text-slate-300 uppercase text-[11px]">${cat.label}</span>
        <span class="text-cyan-400">${cat.v2}</span>
      </div>
      <div class="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden flex border border-slate-800">
        <div class="h-full bg-amber-500 rounded-full" style="width: ${p1Pct}%"></div>
        <div class="h-full bg-cyan-500 rounded-full ml-0.5" style="width: ${p2Pct}%"></div>
      </div>
    `;
    container.appendChild(row);
  });
}

// -----------------------------------------------------------------------------
// 🔥 СИМУЛЯЦИЯ МАТЧА 5х5: 2 ТАЙМА, ФОЛЫ, ДАБЛ-ПЕНАЛЬТИ, 5-Й ПОЛЕВОЙ И MVP
// -----------------------------------------------------------------------------
async function startTeam5x5Match() {
  if (isTeamMatchRunning || !currentBattleTeam1 || !currentBattleTeam2) return;
  isTeamMatchRunning = true;

  const arena = document.getElementById("team-match-arena");
  const eventsContainer = document.getElementById("team-match-events-container");
  const summary = document.getElementById("team-match-summary");
  const scoreT1El = document.getElementById("match-score-t1");
  const scoreT2El = document.getElementById("match-score-t2");
  const scoreT1Name = document.getElementById("match-score-t1-name");
  const scoreT2Name = document.getElementById("match-score-t2-name");
  const minuteEl = document.getElementById("team-match-minute");
  const fouls1El = document.getElementById("team-1-fouls");
  const fouls2El = document.getElementById("team-2-fouls");

  if (!arena || !eventsContainer) return;

  arena.classList.remove("hidden");
  summary.classList.add("hidden");
  eventsContainer.innerHTML = "";
  scoreT1El.innerText = "0";
  scoreT2El.innerText = "0";
  scoreT1Name.innerText = currentBattleTeam1.name;
  scoreT2Name.innerText = currentBattleTeam2.name;
  fouls1El.innerText = "0 / 5";
  fouls2El.innerText = "0 / 5";

  arena.scrollIntoView({ behavior: "smooth", block: "center" });

  const r1 = calculateTeamRatings(currentBattleTeam1);
  const r2 = calculateTeamRatings(currentBattleTeam2);

  const t1Scorers = currentBattleTeam1.players;
  const t2Scorers = currentBattleTeam2.players;

  let score1 = 0;
  let score2 = 0;
  let fouls1 = 0;
  let fouls2 = 0;
  const matchGoals = [];

  const matchTimeline = [
    // 1-й тайм (1 - 25 мин)
    { min: "4'", type: "attack", text: `Разведка боем! ${t1Scorers[0].name} плотно заряжает в ближний угол — вратарь переводит на угловой!` },
    { min: "9'", type: "goal", team: 1, scorer: t1Scorers[0].name, text: `ГО-О-ОЛ! 1:0! ${t1Scorers[0].name} замыкает прострел подошвой в касание на дальней штанге!` },
    { min: "14'", type: "foul", team: 2, text: `Опасный фол в центре площадки: срыв быстрой контратаки 2 в 1.` },
    { min: "19'", type: "goal", team: 2, scorer: t2Scorers[1].name, text: `ГО-О-ОЛ! 1:1! ${t2Scorers[1].name} накручивает двоих на фланге и кладёт с носка в девятку!` },
    { min: "24'", type: "save", text: `Сейв тайма! Вратарь гостей вытягивается в шпагате на самой ленточке ворот!` },
    { min: "25'", type: "halftime", text: `ПЕРЕРЫВ! Равный, высочайший темп мини-футбола в первом тайме.` },

    // 2-й тайм (26 - 50 мин)
    { min: "29'", type: "goal", team: 1, scorer: t1Scorers[1].name, text: `ГО-О-ОЛ! 2:1! Розыгрыш углового под удар низом — ${t1Scorers[1].name} шьёт сквозь частокол ног!` },
    { min: "35'", type: "foul", team: 1, text: `Жёсткий стык у борта! 5-й командный фол — хозяева висят на волоске от дабл-пенальти!` },
    { min: "41'", type: "goal", team: 2, scorer: t2Scorers[0].name, text: `ГО-О-ОЛ! 2:2! ${t2Scorers[0].name} продавливает последнего защитника и разворачивается с ударом!` },
    { min: "46'", type: "double_penalty", team: 2, scorer: t2Scorers[0].name, text: `6-Й ФОЛ! 10-метровый дабл-пенальти без стенки! ${t2Scorers[0].name} хладнокровно разводит вратаря и мяч!` },
    { min: "48'", type: "fifth_field", team: 1, text: `ВА-БАНК! Хозяева снимают вратаря и выпускают 5-го полевого в манишке!` },
    { min: "49'", type: "clutch_goal", team: 1, scorer: t1Scorers[0].name, text: `БЕЗУМИЕ НА 49-Й МИНУТЕ! Раскатали впятером до верного: ${t1Scorers[0].name} заносит мяч в пустые ворота!` },
    { min: "50'", type: "fulltime", text: `ФИНАЛЬНАЯ СИРЕНА! Валидольный матч 5х5 закончен под аплодисменты зала!` }
  ];

  for (let i = 0; i < matchTimeline.length; i++) {
    await new Promise(r => setTimeout(r, 650));

    const ev = matchTimeline[i];
    minuteEl.innerText = `${ev.min} мин`;

    let eventColor = "border-slate-800 text-slate-300";
    let icon = "fa-futbol";

    if (ev.type === "goal" || ev.type === "clutch_goal" || ev.type === "double_penalty") {
      if (ev.team === 1) {
        score1++;
        scoreT1El.innerText = score1;
        eventColor = "border-amber-500/50 bg-amber-500/10 text-amber-200";
        matchGoals.push({ team: 1, min: ev.min, scorer: ev.scorer });
      } else {
        score2++;
        scoreT2El.innerText = score2;
        eventColor = "border-cyan-500/50 bg-cyan-500/10 text-cyan-200";
        matchGoals.push({ team: 2, min: ev.min, scorer: ev.scorer });
      }
      icon = "fa-fire";
    } else if (ev.type === "foul") {
      if (ev.team === 1) fouls1++;
      else fouls2++;
      fouls1El.innerText = `${fouls1} / 5`;
      fouls2El.innerText = `${fouls2} / 5`;
      eventColor = "border-yellow-500/40 bg-yellow-500/10 text-yellow-300";
      icon = "fa-triangle-exclamation";
    } else if (ev.type === "halftime") {
      fouls1 = 0; fouls2 = 0;
      fouls1El.innerText = "0 / 5"; fouls2El.innerText = "0 / 5";
      eventColor = "border-slate-700 bg-slate-900 text-slate-400 font-bold";
      icon = "fa-pause";
    }

    const eventEl = document.createElement("div");
    eventEl.className = `p-2.5 rounded-xl border ${eventColor} text-xs flex items-center gap-3 transition-all`;
    eventEl.innerHTML = `
      <span class="font-black text-amber-400 text-xs shrink-0 w-8">${ev.min}</span>
      <i class="fa-solid ${icon} shrink-0 text-sm"></i>
      <span class="flex-1">${ev.text}</span>
    `;
    eventsContainer.appendChild(eventEl);
    eventsContainer.scrollTop = eventsContainer.scrollHeight;
  }

  await new Promise(r => setTimeout(r, 600));

  summary.classList.remove("hidden");
  summary.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const mvpCandidate = score1 >= score2 ? t1Scorers[0].name : t2Scorers[0].name;

  summary.innerHTML = `
    <div class="text-4xl mb-2">🏆⚽</div>
    <h4 class="text-xl font-black text-white mb-1">
      ИТОГ МАТЧА: <span class="text-amber-400">${currentBattleTeam1.name}</span> ${score1} : ${score2} <span class="text-cyan-400">${currentBattleTeam2.name}</span>
    </h4>
    <p class="text-xs font-bold text-emerald-400 mb-3">⭐ ИГРОК МАТЧА (MVP): <b>${mvpCandidate}</b> (решающий вклад в результат)</p>
    
    <div class="text-xs text-slate-300 bg-slate-950/70 p-3 rounded-xl border border-slate-800 max-w-lg mx-auto mb-4 text-left space-y-1">
      <div class="font-bold text-slate-400 uppercase text-[10px] mb-1">📋 Протокол голов:</div>
      ${matchGoals.map(g => `<div class="${g.team === 1 ? 'text-amber-300' : 'text-cyan-300'}">● ${g.min} — <b>${g.scorer}</b> (${g.team === 1 ? currentBattleTeam1.name : currentBattleTeam2.name})</div>`).join("")}
    </div>

    <div>
      <button onclick="startTeam5x5Match()" class="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-slate-950 font-black text-xs uppercase tracking-wider transition shadow">
        <i class="fa-solid fa-rotate-right mr-1"></i> Сыграть матч-реванш 5х5
      </button>
    </div>
  `;

  isTeamMatchRunning = false;
}

function updateH2H() {
  updateDuelDisplay();
  renderDuelComparisonBars();
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

  const pName = (document.getElementById("input-name")?.value || "").trim();
  if (pName) {
    const key = "futsal_avatar_" + pName.toLowerCase();
    try {
      localStorage.setItem(key, dataUrl);
    } catch (e) {
      console.warn("localStorage quota:", e);
    }

    // Сохраняем сразу в постоянную БД SQLite через API
    fetch(API_BASE + "/avatar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: pName, avatar: dataUrl })
    }).catch(err => console.warn("Avatar sync error:", err));
  }

  saveCardStateToStorage();
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


// =============================================================================
// Стартовая пятёрка (Lineup 5x5) и интерактивный паркет
// =============================================================================
const FORMATIONS = {
  "1-2-1": {
    name: "1-2-1 «Ромб»",
    slots: [
      { id: 0, pos: "GK", label: "Вратарь (GK)", x: 50, y: 86 },
      { id: 1, pos: "FIX", label: "Столб/Фиксо (FIX)", x: 50, y: 64 },
      { id: 2, pos: "ALA", label: "Левая бровка (L.ALA)", x: 20, y: 46 },
      { id: 3, pos: "ALA", label: "Правая бровка (R.ALA)", x: 80, y: 46 },
      { id: 4, pos: "PIV", label: "Наконечник (PIV)", x: 50, y: 20 }
    ],
    balance: "Классический баланс (Ромб)",
    tacticTip: "Контроль мяча через ромб, изоляция столпа спиной к чужим воротам и резкие включения бровки на дальнюю штангу."
  },
  "2-2": {
    name: "2-2 «Квадрат»",
    slots: [
      { id: 0, pos: "GK", label: "Вратарь (GK)", x: 50, y: 86 },
      { id: 1, pos: "FIX", label: "Левый защитник (L.FIX)", x: 28, y: 64 },
      { id: 2, pos: "FIX", label: "Правый защитник (R.FIX)", x: 72, y: 64 },
      { id: 3, pos: "PIV", label: "Левый форвард (L.PIV)", x: 28, y: 24 },
      { id: 4, pos: "PIV", label: "Правый форвард (R.PIV)", x: 72, y: 24 }
    ],
    balance: "Оборонительный блок / Контратаки",
    tacticTip: "Плотная пара сзади блокирует центр, форварды на скорости убегают 2-в-2 при первом же перехвате."
  },
  "3-1": {
    name: "3-1 «Пирамида»",
    slots: [
      { id: 0, pos: "GK", label: "Вратарь (GK)", x: 50, y: 86 },
      { id: 1, pos: "ALA", label: "Левый инсайд (L.ALA)", x: 22, y: 56 },
      { id: 2, pos: "FIX", label: "Опорный защитник (FIX)", x: 50, y: 66 },
      { id: 3, pos: "ALA", label: "Правый инсайд (R.ALA)", x: 78, y: 56 },
      { id: 4, pos: "PIV", label: "Чистый столп (PIV)", x: 50, y: 18 }
    ],
    balance: "Атака через мощного столпа",
    tacticTip: "Тройка держит мяч перед штрафной, выводя одного столпа на удар с разворота и сбросы."
  },
  "5-0": {
    name: "5 полевых (Power Play)",
    slots: [
      { id: 0, pos: "GK", label: "Гонила (Fly GK)", x: 20, y: 50 },
      { id: 1, pos: "FIX", label: "Разыгрывающий (FIX)", x: 50, y: 58 },
      { id: 2, pos: "ALA", label: "Правая бровка (ALA)", x: 80, y: 50 },
      { id: 3, pos: "PIV", label: "Левая штанга (PIV)", x: 28, y: 20 },
      { id: 4, pos: "PIV", label: "Правая штанга (PIV)", x: 72, y: 20 }
    ],
    balance: "Тотальный навал / 5-й полевой",
    tacticTip: "Вратарь снят! Раскатка пятеркой в чужой зоне, поиск замыкания на дальней штанге. Любая потеря — удар по пустым!"
  }
};

let currentLineupFormationKey = "1-2-1";
let currentLineup = [null, null, null, null, null];
let selectedLineupSlot = null;
let currentBenchFilter = "ALL";
let cachedBenchFavorites = [];

function formatShortName(fullName) {
  if (!fullName) return "Игрок";
  const parts = fullName.trim().split(/\s+/);
  if (parts.length >= 2) {
    return parts[0] + " " + parts[1][0] + ".";
  }
  return parts[0];
}

function calculatePlayerOVR(p) {
  if (!p) return 75;
  const m = Math.max(1, p.matches || 1);
  const g = p.goals || 0;
  const a = p.assists || 0;
  const pts = (g + a) / m;
  const base = 75 + Math.min(15, Math.round(pts * 10)) + Math.min(5, (p.mvp_count || 0));
  return Math.max(70, Math.min(95, base));
}

function getQuickScoutFact(p) {
  if (!p) return "";
  const m = Math.max(1, p.matches || 1);
  const g = p.goals || 0;
  const a = p.assists || 0;
  const pos = p.position || "ALA";

  if (pos === "GK") return "🧤 Надежен на ленточке, страхует выходы";
  if (g / m >= 0.8) return "🔥 Киллер штрафной (" + (g / m).toFixed(1) + " гола за игру)";
  if (a > g) return "🎯 Главный плеймейкер (больше ассистов, чем голов)";
  if (p.yellow_cards >= 3) return "⚡ Жесткий боец, идет в подкаты до конца";
  return "⭐ Универсал, отрабатывает по всей бровке";
}

function initLineup() {
  try {
    const saved = localStorage.getItem("futsal_lineup_5x5");
    if (saved) {
      currentLineup = JSON.parse(saved);
      if (!Array.isArray(currentLineup) || currentLineup.length !== 5) {
        currentLineup = [null, null, null, null, null];
      }
    }
    const savedForm = localStorage.getItem("futsal_lineup_formation");
    if (savedForm && FORMATIONS[savedForm]) {
      currentLineupFormationKey = savedForm;
      const sel = document.getElementById("lineup-formation-select");
      if (sel) sel.value = savedForm;
    }
  } catch (e) {
    console.warn("Could not load saved lineup:", e);
  }

  renderLineupCourt();
  loadBenchPlayers();
  updateSquadAnalytics();
}

function changeLineupFormation(key) {
  if (!FORMATIONS[key]) return;
  currentLineupFormationKey = key;
  localStorage.setItem("futsal_lineup_formation", key);
  renderLineupCourt();
  updateSquadAnalytics();
}

function renderLineupCourt() {
  const layer = document.getElementById("court-players-layer");
  if (!layer) return;

  const formation = FORMATIONS[currentLineupFormationKey] || FORMATIONS["1-2-1"];
  layer.innerHTML = "";

  formation.slots.forEach(slot => {
    const player = currentLineup[slot.id];
    const isSelected = selectedLineupSlot === slot.id;
    const isTopHalf = slot.y < 35;
    const tooltipPosition = isTopHalf ? "top-full mt-3" : "bottom-full mb-3";

    const slotEl = document.createElement("div");
    slotEl.className = "absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center select-none z-20";
    slotEl.style.left = slot.x + "%";
    slotEl.style.top = slot.y + "%";

    if (player) {
      const ovr = calculatePlayerOVR(player);
      const avSrc = player.avatar || DEFAULT_AVATAR;
      const shortName = formatShortName(player.name);

      slotEl.innerHTML = `
        <div class="relative group cursor-pointer flex flex-col items-center">
          <!-- Аватар игрока на паркете -->
          <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl relative shadow-2xl border-2 ${isSelected ? 'border-emerald-400 ring-4 ring-emerald-400/50 scale-105' : 'border-amber-400 hover:border-amber-300'} overflow-hidden transition-all bg-slate-900 group-hover:scale-105">
            <img src="${avSrc}" class="w-full h-full object-cover">
            <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-80 pointer-events-none"></div>
            
            <!-- Бейдж позиции и рейтинга OVR внизу жетона -->
            <div class="absolute bottom-0 inset-x-0 bg-slate-950/90 text-amber-400 text-[10px] sm:text-[11px] font-black text-center py-0.5 border-t border-amber-400/30">
              ${player.position || slot.pos} · ${ovr}
            </div>

            <!-- Кнопка удаления с поля при наведении -->
            <button onclick="event.stopPropagation(); removePlayerFromSlot(${slot.id})" class="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-600/90 hover:bg-red-500 text-white text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition shadow" title="Убрать с поля">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <!-- Имя игрока под жетоном -->
          <div class="mt-1 px-2 py-0.5 rounded-md bg-slate-950/90 border border-slate-700/80 shadow text-center">
            <span class="text-[10px] sm:text-[11px] font-black text-white truncate max-w-[85px] block">${shortName}</span>
          </div>

          <!-- ВСПЛЫВАЮЩЕЕ ОКНО СО СТАТИСТИКОЙ ПРИ НАВЕДЕНИИ (HOVER POPUP) -->
          <div class="absolute ${tooltipPosition} left-1/2 -translate-x-1/2 w-64 bg-slate-950/95 border-2 border-amber-400/90 rounded-2xl p-3.5 shadow-2xl backdrop-blur-md z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-all duration-200 transform scale-95 group-hover:scale-100">
            <!-- Шапка карточки -->
            <div class="flex items-center gap-2.5 pb-2 border-b border-slate-800">
              <img src="${avSrc}" class="w-10 h-12 rounded-xl object-cover border border-amber-400/40 bg-slate-900 shadow shrink-0">
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5">
                  <span class="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">${player.position || slot.pos}</span>
                  <span class="text-[10px] font-black text-amber-400">${ovr} OVR</span>
                </div>
                <h5 class="text-xs font-black text-white truncate mt-0.5">${player.name}</h5>
                <p class="text-[10px] text-slate-400 truncate">${player.team || "Без команды"}</p>
              </div>
            </div>

            <!-- Сетка статистики -->
            <div class="grid grid-cols-2 gap-1.5 my-2 text-[11px]">
              <div class="bg-slate-900/80 px-2 py-1 rounded-lg border border-slate-800/80">
                <span class="text-slate-400 text-[9px] block uppercase font-bold">Матчи:</span>
                <span class="font-black text-white">${player.matches || 0}</span>
              </div>
              <div class="bg-slate-900/80 px-2 py-1 rounded-lg border border-slate-800/80">
                <span class="text-slate-400 text-[9px] block uppercase font-bold">Голы:</span>
                <span class="font-black text-amber-400">${player.goals || 0}</span>
              </div>
              <div class="bg-slate-900/80 px-2 py-1 rounded-lg border border-slate-800/80">
                <span class="text-slate-400 text-[9px] block uppercase font-bold">Пасы:</span>
                <span class="font-black text-sky-400">${player.assists || 0}</span>
              </div>
              <div class="bg-slate-900/80 px-2 py-1 rounded-lg border border-slate-800/80">
                <span class="text-slate-400 text-[9px] block uppercase font-bold">ЖК / КК:</span>
                <span class="font-black text-yellow-400">${player.yellow_cards || 0} / ${player.red_cards || 0}</span>
              </div>
            </div>

            <!-- Скаутская фишка -->
            <div class="text-[10px] text-amber-300/90 italic bg-amber-500/10 px-2 py-1 rounded-md border border-amber-500/20">
              ${getQuickScoutFact(player)}
            </div>
            <div class="text-[9px] text-slate-500 text-center mt-1.5">Кликните слот для замены игрока</div>
          </div>
        </div>
      `;
      slotEl.onclick = () => selectSlot(slot.id);
    } else {
      // Пустой слот для игрока
      slotEl.innerHTML = `
        <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl border-2 border-dashed ${isSelected ? 'border-emerald-300 bg-emerald-500/30 scale-105 ring-4 ring-emerald-400/50' : 'border-emerald-400/50 bg-slate-950/60 hover:bg-emerald-500/20 hover:border-emerald-300'} cursor-pointer flex flex-col items-center justify-center transition-all group shadow-lg">
          <i class="fa-solid fa-plus text-emerald-400 text-sm group-hover:scale-125 transition-transform"></i>
          <span class="text-[10px] font-black text-emerald-300 uppercase mt-0.5 tracking-wider">${slot.pos}</span>
        </div>
        <div class="mt-1 px-2 py-0.5 rounded-md bg-slate-950/90 border border-slate-800 text-center">
          <span class="text-[10px] font-bold text-slate-300">${slot.label.split(' ')[0]}</span>
        </div>
      `;
      slotEl.onclick = () => selectSlot(slot.id);
    }

    layer.appendChild(slotEl);
  });
}

function selectSlot(slotId) {
  if (selectedLineupSlot === slotId) {
    selectedLineupSlot = null;
  } else {
    selectedLineupSlot = slotId;
  }
  renderLineupCourt();
  highlightBenchForSlot(selectedLineupSlot);
}

function highlightBenchForSlot(slotId) {
  const formation = FORMATIONS[currentLineupFormationKey];
  if (slotId !== null && formation && formation.slots[slotId]) {
    const pos = formation.slots[slotId].pos;
    filterBench(pos);
  }
}

async function loadBenchPlayers() {
  const container = document.getElementById("bench-players-list");
  const countEl = document.getElementById("bench-count");
  if (!container) return;

  container.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin mr-1 text-amber-400"></i> Загрузка скамейки...</div>';

  const favs = await fetchWithFallback(API_BASE + "/favorites");
  cachedBenchFavorites = favs || [];

  if (countEl) countEl.innerText = cachedBenchFavorites.length + " игроков";

  renderBenchCards();
}

function filterBench(pos) {
  currentBenchFilter = pos;
  document.querySelectorAll(".bench-filter-btn").forEach(btn => {
    if (btn.getAttribute("data-pos") === pos) {
      btn.className = "bench-filter-btn px-2.5 py-1 rounded-lg bg-amber-500 text-slate-950 font-black shadow";
    } else {
      btn.className = "bench-filter-btn px-2 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 font-bold";
    }
  });
  renderBenchCards();
}

function renderBenchCards() {
  const container = document.getElementById("bench-players-list");
  if (!container) return;

  let list = cachedBenchFavorites;
  if (currentBenchFilter && currentBenchFilter !== "ALL") {
    list = list.filter(p => (p.position || "ALA").toUpperCase() === currentBenchFilter.toUpperCase());
  }

  if (list.length === 0) {
    container.innerHTML = '<div class="text-center py-8 text-slate-500 text-xs"><i class="fa-solid fa-star text-slate-700 text-2xl mb-2"></i><div>Нет подходящих игроков в избранном.</div><p class="text-[11px] text-slate-600 mt-1">Добавьте игроков через поиск по лигам!</p></div>';
    return;
  }

  container.innerHTML = "";
  list.forEach(p => {
    const isAlreadyOnField = currentLineup.some(lp => lp && String(lp.id || lp.name) === String(p.id || p.name));
    const avSrc = p.avatar || DEFAULT_AVATAR;
    const ovr = calculatePlayerOVR(p);

    const card = document.createElement("div");
    card.className = "bg-slate-900/90 border " + (isAlreadyOnField ? "border-emerald-500/40 opacity-70" : "border-slate-800 hover:border-amber-500/50") + " p-2.5 rounded-xl flex items-center justify-between gap-3 text-xs transition shadow";

    card.innerHTML = `
      <div class="flex items-center gap-2.5 min-w-0 flex-1">
        <img src="${avSrc}" class="w-9 h-11 rounded-lg object-cover border border-amber-400/30 bg-slate-950 shrink-0">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-1.5">
            <span class="text-[9px] font-black uppercase px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">${p.position || 'ALA'}</span>
            <span class="text-[10px] font-black text-amber-400">${ovr} OVR</span>
            ${isAlreadyOnField ? '<span class="text-[9px] font-bold text-emerald-400">На поле</span>' : ''}
          </div>
          <h4 class="font-black text-white truncate text-xs mt-0.5">${p.name}</h4>
          <p class="text-[10px] text-slate-400">${p.matches} игр · <b class="text-amber-400">${p.goals} г</b> · <b class="text-sky-400">${p.assists} п</b></p>
        </div>
      </div>
      <button onclick="handleBenchPlayerClick(${p.id})" class="shrink-0 px-2.5 py-1.5 rounded-lg text-xs font-bold transition ${isAlreadyOnField ? 'bg-slate-800 text-slate-400 hover:bg-slate-700' : 'bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-black shadow'}">
        ${isAlreadyOnField ? 'Заменить' : 'В состав'}
      </button>
    `;

    container.appendChild(card);
  });
}

function handleBenchPlayerClick(playerId) {
  const player = cachedBenchFavorites.find(p => p.id === playerId);
  if (!player) return;

  // Если выбран конкретный слот на паркете
  if (selectedLineupSlot !== null) {
    assignPlayerToSlot(player, selectedLineupSlot);
    selectedLineupSlot = null;
    return;
  }

  // Иначе ищем первый пустой слот, соответствующий позиции игрока
  const formation = FORMATIONS[currentLineupFormationKey];
  let targetSlot = null;

  for (let i = 0; i < formation.slots.length; i++) {
    if (currentLineup[i] === null && formation.slots[i].pos === (player.position || 'ALA')) {
      targetSlot = i;
      break;
    }
  }

  // Если точного по позиции нет, берем любой пустой
  if (targetSlot === null) {
    for (let i = 0; i < formation.slots.length; i++) {
      if (currentLineup[i] === null) {
        targetSlot = i;
        break;
      }
    }
  }

  if (targetSlot !== null) {
    assignPlayerToSlot(player, targetSlot);
  } else {
    // Если все 5 слотов заняты, заменяем 1-го полевого
    assignPlayerToSlot(player, 4);
  }
}

function assignPlayerToSlot(player, slotId) {
  currentLineup[slotId] = player;
  saveLineupToStorage();
  renderLineupCourt();
  renderBenchCards();
  updateSquadAnalytics();
  confetti({ particleCount: 35, spread: 50, origin: { y: 0.7 } });
}

function removePlayerFromSlot(slotId) {
  currentLineup[slotId] = null;
  saveLineupToStorage();
  renderLineupCourt();
  renderBenchCards();
  updateSquadAnalytics();
}

function clearLineupCourt() {
  if (!confirm("Очистить все позиции на паркете?")) return;
  currentLineup = [null, null, null, null, null];
  saveLineupToStorage();
  renderLineupCourt();
  renderBenchCards();
  updateSquadAnalytics();
}

function saveLineupToStorage() {
  try {
    localStorage.setItem("futsal_lineup_5x5", JSON.stringify(currentLineup));
  } catch (e) {
    console.warn("Storage error:", e);
  }
}

function updateSquadAnalytics() {
  const activePlayers = currentLineup.filter(Boolean);
  const avgOvrEl = document.getElementById("lineup-avg-ovr");
  const totalGoalsEl = document.getElementById("lineup-total-goals");
  const totalMatchesEl = document.getElementById("lineup-total-matches");
  const balanceEl = document.getElementById("lineup-squad-balance");
  const verdictEl = document.getElementById("lineup-coach-verdict");

  if (!avgOvrEl) return;

  if (activePlayers.length === 0) {
    avgOvrEl.innerText = "--";
    totalGoalsEl.innerText = "0";
    totalMatchesEl.innerText = "0";
    balanceEl.innerText = "Пустой состав";
    balanceEl.className = "text-[10px] font-black uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700";
    verdictEl.innerText = "Заполните позиции на паркете игроками из избранного, чтобы получить тактический разбор.";
    return;
  }

  let totalGoals = 0;
  let totalMatches = 0;
  let totalOvr = 0;

  activePlayers.forEach(p => {
    totalGoals += (p.goals || 0);
    totalMatches += (p.matches || 0);
    totalOvr += calculatePlayerOVR(p);
  });

  const avgOvr = Math.round(totalOvr / activePlayers.length);
  avgOvrEl.innerText = avgOvr;
  totalGoalsEl.innerText = totalGoals;
  totalMatchesEl.innerText = totalMatches;

  const formation = FORMATIONS[currentLineupFormationKey];
  balanceEl.innerText = formation ? formation.balance : "Сбалансированная";
  balanceEl.className = "text-[10px] font-black uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";

  if (activePlayers.length === 5) {
    verdictEl.innerHTML = "🏆 <b>Стартовая пятёрка укомплектована!</b> Суммарно на паркете <b class='text-amber-400'>" + totalGoals + " голов</b> в " + totalMatches + " матчах. " + (formation ? formation.tacticTip : "");
  } else {
    verdictEl.innerText = "В составе " + activePlayers.length + " из 5 игроков. Добавьте ещё " + (5 - activePlayers.length) + ", чтобы завершить стартовую пятёрку.";
  }
}

function exportLineupCourt() {
  const container = document.getElementById("futsal-court-container");
  if (!container) return;

  html2canvas(container, {
    scale: 2,
    useCORS: true,
    backgroundColor: null
  }).then(canvas => {
    const link = document.createElement("a");
    link.download = "futsal-lineup-5x5-" + currentLineupFormationKey + ".png";
    link.href = canvas.toDataURL("image/png");
    link.click();
    confetti({ particleCount: 60, spread: 70, origin: { y: 0.6 } });
  }).catch(err => {
    alert("Ошибка экспорта изображения: " + err);
  });
}
