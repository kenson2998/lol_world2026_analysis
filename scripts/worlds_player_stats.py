"""Pull per-player Worlds game stats from gol.gg full-stats pages into data/worlds.json (key "player_games").

Each finished match needs `draft_source` (a gol.gg game URL), `blue`/`red` and a draft (for champions).
usage: python3 -I worlds_player_stats.py data_dir cache_dir
"""
import json, os, re, subprocess, sys

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"
ROLES = {"TOP": "top", "JUNGLE": "jungle", "MID": "mid", "ADC": "bot", "SUPPORT": "support"}
# gol.gg row label -> our key
METRICS = {"Kills": "k", "Deaths": "d", "Assists": "a", "CS": "cs", "CSM": "csm", "Golds": "gold", "GPM": "gpm",
           "GOLD%": "gold_pct", "Vision Score": "vs", "VSPM": "vspm", "Wards placed": "wards", "Total damage to Champion": "dmg",
           "DPM": "dpm", "DMG%": "dmg_pct", "KP%": "kp", "Solo kills": "solo", "Objectives Stolen": "steals", "Total damage taken": "dmg_taken", "GD@15": "gd15", "CSD@15": "csd15", "XPD@15": "xpd15"}


def fetch(game_id, cache):
    path = os.path.join(cache, f"{game_id}.html")
    if not os.path.exists(path) or os.path.getsize(path) < 10000:
        subprocess.run(["curl", "-s", "-L", "--max-time", "40", "-A", UA, "-o", path,
                        f"https://gol.gg/game/stats/{game_id}/page-fullstats/"], check=True)
    return open(path, errors="ignore").read()


def num(v):
    v = v.replace("%", "").replace(",", "").strip()
    try:
        return float(v)
    except ValueError:
        return None


def parse(html):
    table = re.search(r"<table.*?</table>", html, re.S).group(0)
    rows = {}
    for r in re.findall(r"<tr.*?</tr>", table, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        if cells and cells[0]:
            rows[cells[0]] = cells[1:]
    return rows


def main(data_dir, cache):
    os.makedirs(cache, exist_ok=True)
    wpath = f"{data_dir}/worlds.json"
    w = json.load(open(wpath))
    rosters = {t["team"]: t for t in json.load(open(f"{data_dir}/rosters.json"))}
    out = []
    for ri, rnd in enumerate(w["rounds"]):
        if rnd["status"] == "upcoming":
            continue
        # a Bo3 keeps its games in m["games"]; a Bo1 match is its own single game
        for m in (m for m in rnd["matches"] if m.get("winner")):
            games = m.get("games") or [m]
            for gi, g in enumerate(games):
                label = f'{m["a"]} vs {m["b"]}' + (f" G{gi + 1}" if len(games) > 1 else "")
                gid = re.search(r"/stats/(\d+)/", g.get("draft_source", ""))
                if not gid:
                    print(f"skip {label}: no gol.gg id", file=sys.stderr)
                    continue
                rows = parse(fetch(gid.group(1), cache))
                champ = {(p["team"], p["role"]): p["champion"] for p in g["draft"]["picks"]}
                for i, role_raw in enumerate(rows["Role"]):
                    team = g["blue"] if i < 5 else g["red"]
                    role = ROLES[role_raw]
                    rec = {"round": ri, "match": label, "team": team, "role": role,
                           "player": rosters[team][role], "gol_name": rows["Player"][i], "champion": champ.get((team, role)),
                           "win": g["winner"] == team, "length": g.get("length")}
                    for lbl, key in METRICS.items():
                        if lbl in rows and i < len(rows[lbl]):
                            rec[key] = num(rows[lbl][i])
                    out.append(rec)
                # objectives the other team stole this game count against the jungler (the one holding Smite)
                recs = out[-10:]
                for r in recs:
                    if r["role"] == "jungle":
                        r["stolen_against"] = sum(x.get("steals") or 0 for x in recs if x["team"] != r["team"])
                print(f"{label}: gol {gid.group(1)} ok", file=sys.stderr)
    w["player_games"] = out
    json.dump(w, open(wpath, "w"), ensure_ascii=False, indent=1)
    print(f"{len(out)} player-games", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
