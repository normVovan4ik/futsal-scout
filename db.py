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
    conn.close()


def save_favorite(player_data: dict) -> int:
    conn = get_db()
    name = player_data.get("name", "").strip()
    sources_data = json.dumps(player_data.get("sources_data", {}), ensure_ascii=False)

    with conn:
        # Проверяем, есть ли уже такой игрок
        cur = conn.execute("SELECT id FROM favorites WHERE name = ?", (name,))
        row = cur.fetchone()
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
                "avatar": player_data.get("avatar", ""),
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
                "avatar": player_data.get("avatar", ""),
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
