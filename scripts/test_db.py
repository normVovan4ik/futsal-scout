import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import db
import json

# Test save
p = {
    "name": "Ершов Владимир",
    "position": "PIV",
    "team": "Спартак 5х5",
    "matches": 68,
    "team_matches": 68,
    "goals": 102,
    "assists": 30,
    "yellow_cards": 7,
    "red_cards": 0,
    "mvp_count": 1,
    "sources_data": {
        "ligastart": {"matches": 68, "goals": 102, "assists": 30}
    },
    "notes": "Основной форвард, гроза любительской лиги"
}
fid = db.save_favorite(p)
print("Saved favorite id:", fid)
all_f = db.get_all_favorites()
print("All favorites count:", len(all_f))
print("First favorite:", all_f[0]["name"])
