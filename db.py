"""
SQLite Database для Futsal Scout
Хранение избранных игроков и их настроек.
"""

import sqlite3
import json
import os
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "futsal_scout.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT DEFAULT 'PIV',
                team TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                matches INTEGER DEFAULT 0,
                team_matches INTEGER DEFAULT 0,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                yellow_cards INTEGER DEFAULT 0,
                red_cards INTEGER DEFAULT 0,
                mvp_count INTEGER DEFAULT 0,
                sources_data TEXT DEFAULT '{}',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_avatars (
                player_name TEXT PRIMARY KEY,
                avatar TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.close()


def save_avatar(player_name: str, avatar_data: str) -> bool:
    """Сохраняет аватар игрока в постоянную таблицу player_avatars и обновляет в избранном."""
    name_clean = player_name.strip()
    if not name_clean or not avatar_data:
        return False

    canon_key = " ".join(name_clean.lower().split()[:2])
    conn = get_db()
    with conn:
        conn.execute("""
            INSERT INTO player_avatars (player_name, avatar, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_name) DO UPDATE SET
                avatar = excluded.avatar,
                updated_at = CURRENT_TIMESTAMP
        """, (canon_key, avatar_data))

        # Обновляем также в избранном если игрок там есть
        conn.execute("""
            UPDATE favorites SET avatar = ?
            WHERE LOWER(TRIM(name)) LIKE ?
        """, (avatar_data, f"%{canon_key}%"))
    conn.close()
    return True


def get_avatar(player_name: str) -> Optional[str]:
    """Возвращает сохраненный аватар игрока по имени."""
    name_clean = player_name.strip()
    if not name_clean:
        return None

    canon_key = " ".join(name_clean.lower().split()[:2])
    conn = get_db()
    cur = conn.execute("SELECT avatar FROM player_avatars WHERE player_name = ?", (canon_key,))
    row = cur.fetchone()
    if row and row["avatar"]:
        conn.close()
        return row["avatar"]

    # Fallback на favorites
    cur2 = conn.execute("SELECT avatar FROM favorites WHERE LOWER(TRIM(name)) LIKE ? AND avatar != '' LIMIT 1", (f"%{canon_key}%",))
    row2 = cur2.fetchone()
    conn.close()
    return row2["avatar"] if row2 else None


def save_favorite(player_data: dict) -> int:
    conn = get_db()
    name = player_data.get("name", "").strip()
    sources_data = json.dumps(player_data.get("sources_data", {}), ensure_ascii=False)
    canon_key = " ".join(name.lower().split()[:2])

    # Если передан непустой аватар, сохраняем его в постоянную таблицу
    incoming_avatar = player_data.get("avatar", "").strip()
    if incoming_avatar and not incoming_avatar.startswith("data:image/svg"):
        save_avatar(name, incoming_avatar)

    with conn:
        cur = conn.execute("SELECT id, avatar FROM favorites WHERE name = ?", (name,))
        row = cur.fetchone()

        # Определяем итоговый аватар: не затираем существующий пустым значением
        final_avatar = incoming_avatar
        if not final_avatar or final_avatar.startswith("data:image/svg"):
            if row and row["avatar"]:
                final_avatar = row["avatar"]
            else:
                saved = get_avatar(name)
                if saved:
                    final_avatar = saved

        if row:
            player_id = row["id"]
            conn.execute("""
                UPDATE favorites SET
                    position = :position,
                    team = :team,
                    avatar = :avatar,
                    matches = :matches,
                    team_matches = :team_matches,
                    goals = :goals,
                    assists = :assists,
                    yellow_cards = :yellow_cards,
                    red_cards = :red_cards,
                    mvp_count = :mvp_count,
                    sources_data = :sources_data,
                    notes = :notes
                WHERE id = :id
            """, {
                "id": player_id,
                "position": player_data.get("position", "PIV"),
                "team": player_data.get("team", ""),
                "avatar": final_avatar,
                "matches": player_data.get("matches", 0),
                "team_matches": player_data.get("team_matches", player_data.get("matches", 0)),
                "goals": player_data.get("goals", 0),
                "assists": player_data.get("assists", 0),
                "yellow_cards": player_data.get("yellow_cards", 0),
                "red_cards": player_data.get("red_cards", 0),
                "mvp_count": player_data.get("mvp_count", 0),
                "sources_data": sources_data,
                "notes": player_data.get("notes", "")
            })
            return player_id
        else:
            cur = conn.execute("""
                INSERT INTO favorites (
                    name, position, team, avatar, matches, team_matches,
                    goals, assists, yellow_cards, red_cards, mvp_count,
                    sources_data, notes
                ) VALUES (
                    :name, :position, :team, :avatar, :matches, :team_matches,
                    :goals, :assists, :yellow_cards, :red_cards, :mvp_count,
                    :sources_data, :notes
                )
            """, {
                "name": name,
                "position": player_data.get("position", "PIV"),
                "team": player_data.get("team", ""),
                "avatar": final_avatar,
                "matches": player_data.get("matches", 0),
                "team_matches": player_data.get("team_matches", player_data.get("matches", 0)),
                "goals": player_data.get("goals", 0),
                "assists": player_data.get("assists", 0),
                "yellow_cards": player_data.get("yellow_cards", 0),
                "red_cards": player_data.get("red_cards", 0),
                "mvp_count": player_data.get("mvp_count", 0),
                "sources_data": sources_data,
                "notes": player_data.get("notes", "")
            })
            return cur.lastrowid


def get_all_favorites() -> List[dict]:
    conn = get_db()
    cur = conn.execute("SELECT * FROM favorites ORDER BY id DESC")
    rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["sources_data"] = json.loads(d["sources_data"] or "{}")
        except Exception:
            d["sources_data"] = {}
        if not d.get("avatar") or d["avatar"].startswith("data:image/svg"):
            saved_av = get_avatar(d.get("name", ""))
            if saved_av:
                d["avatar"] = saved_av
        result.append(d)
    conn.close()
    return result


def delete_favorite(player_id: int) -> bool:
    conn = get_db()
    with conn:
        cur = conn.execute("DELETE FROM favorites WHERE id = ?", (player_id,))
        deleted = cur.rowcount > 0
    conn.close()
    return deleted


# Инициализируем БД при импорте
init_db()
