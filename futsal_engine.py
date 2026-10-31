"""
Futsal Scout Engine (5x5)
Модуль для расчета футзальной статистики и подготовки к парсингу протоколов.
"""

import json
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class FutsalPlayer:
    name: str
    team: str
    position: str  # PIV (Столп), ALA (Бровка), FIX (Защитник), GK (Вратарь)
    matches: int
    team_matches: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    mvp_count: int
    flag_morning_slot: bool = True  # Игры в 9-11 утра
    flag_fifth_player: bool = False  # Подключение 5-го полевого
    flag_backpost: bool = False     # Замыкание дальней штанги


def calculate_futsal_stats(player: FutsalPlayer) -> dict:
    matches = max(1, player.matches)
    team_matches = max(matches, player.team_matches)

    # 1. FIN (Киллер / Финишинг)
    g_per_match = player.goals / matches
    fin = round(45 + min(50, g_per_match * 28) + (4 if player.flag_backpost else 0))

    # 2. VIS (Видение / Плеймейкинг)
    a_per_match = player.assists / matches
    vis = round(45 + min(50, a_per_match * 35))

    # 3. IMP (Импакт / Влияние)
    pts_per_match = (player.goals + player.assists) / matches
    imp = round(40 + min(55, pts_per_match * 22) + (player.mvp_count * 2))

    # 4. DISC (Дисциплина)
    penalty = (player.yellow_cards * 5) + (player.red_cards * 15)
    disc = max(35, round(99 - (penalty / matches * 40)))

    # 5. ATT (Посещаемость / Явка)
    att_rate = matches / team_matches
    att = round(min(99, max(40, att_rate * 99)))

    # 6. CLUTCH (Решала)
    clutch = round(55 + min(40, (player.mvp_count / matches) * 90) + (5 if player.goals > 10 else 0))

    clamp = lambda v: max(30, min(99, v))
    fin, vis, imp, disc, att, clutch = map(clamp, [fin, vis, imp, disc, att, clutch])

    # OVR (Общий рейтинг в зависимости от амплуа)
    pos = player.position.upper()
    if pos == "PIV":
        ovr = round(fin * 0.40 + imp * 0.25 + clutch * 0.15 + att * 0.10 + vis * 0.10)
    elif pos == "ALA":
        ovr = round(vis * 0.30 + imp * 0.25 + fin * 0.20 + att * 0.15 + clutch * 0.10)
    elif pos == "FIX":
        ovr = round(disc * 0.30 + att * 0.25 + imp * 0.20 + clutch * 0.15 + vis * 0.10)
    elif pos == "GK":
        ovr = round(clutch * 0.35 + att * 0.30 + disc * 0.20 + (vis * 0.15 if player.flag_fifth_player else 10))
    else:
        ovr = 75

    ovr = clamp(ovr)

    # Футзальные бейджи
    badges = []
    if att >= 95 and player.flag_morning_slot:
        badges.append("⏰ Будильник в 9:00 (100% явка на ранние матчи)")
    if player.flag_backpost and player.goals >= 5:
        badges.append("🎯 Король дальней штанги")
    if player.assists > player.goals and player.assists >= 6:
        badges.append("🧙‍♂️ Бразильский альтруист (ассистов больше, чем голов)")
    if player.yellow_cards >= 3 or player.red_cards > 0:
        badges.append("🟨 Абонемент на горчичник (регулярные фолы)")
    if player.flag_fifth_player:
        badges.append("👕 Пятый полевой (игра в манишке)")
    if imp >= 88:
        badges.append("👑 Тащит весь район (лидер по результативности)")

    return {
        "player": asdict(player),
        "ratings": {
            "OVR": ovr,
            "FIN": fin,
            "VIS": vis,
            "IMP": imp,
            "DISC": disc,
            "ATT": att,
            "CLUTCH": clutch
        },
        "badges": badges
    }


if __name__ == "__main__":
    demo_player = FutsalPlayer(
        name="Иван Петров",
        team="ЛФК «Зенит» Мини",
        position="PIV",
        matches=14,
        team_matches=14,
        goals=22,
        assists=9,
        yellow_cards=3,
        red_cards=0,
        mvp_count=5,
        flag_morning_slot=True,
        flag_backpost=True
    )

    result = calculate_futsal_stats(demo_player)
    print("=== РЕЗУЛЬТАТ РАСЧЕТА КАРТОЧКИ 5х5 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
