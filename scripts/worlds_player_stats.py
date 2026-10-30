"""Pull per-player Worlds game stats from gol.gg full-stats pages into data/worlds.json (key "player_games").

Each finished match needs `draft_source` (a gol.gg game URL), `blue`/`red` and a draft (for champions).
Games without a gol.gg id (gol.gg down) take their numbers from Leaguepedia scoreboard JSON files, if given:
{"games": [{"match": "MKOI vs T1 G1", "length": "40:00", "players": [{team, role, player, champion, k, d, a, cs, gold, dmg, vs, ...}]}]}
usage: python3 -I worlds_player_stats.py data_dir cache_dir [scoreboards.json ...]
"""
import json, os, re, subprocess, sys

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"
ROLES = {"TOP": "top", "JUNGLE": "jungle", "MID": "mid", "ADC": "bot", "SUPPORT": "support"}
# gol.gg row label -> our key
METRICS = {"Kills": "k", "Deaths": "d", "Assists": "a", "CS": "cs", "CSM": "csm", "Golds": "gold", "GPM": "gpm",
           "GOLD%": "gold_pct", "Vision Score": "vs", "VSPM": "vspm", "Wards placed": "wards", "Total damage to Champion": "dmg",
           "DPM": "dpm", "DMG%": "dmg_pct", "KP%": "kp", "Solo kills": "solo", "Objectives Stolen": "steals", "Total damage taken": "dmg_taken", "GD@15": "gd15", "CSD@15": "csd15", "XPD@15": "xpd15"}


# gol.gg values that are evidently wrong, dropped: (match label, player) -> metric keys
# KC vs CFO G1: Canna's damage taken equals his damage dealt (12770), a copy error on gol.gg
BAD = {("KC vs CFO G1", "Canna"): ["dmg_taken"]}


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


def from_scoreboard(sb, ri, label, g):
    """Player rows for a game gol.gg doesn't have, from a Leaguepedia scoreboard JSON (see usage).

    Leaguepedia gives K/D/A, CS, gold, damage to champions and vision score; per-minute and team-share numbers are
    derived from those, everything else (GD@15, damage taken, solo kills, steals...) stays missing."""
    mins = sum(x * f for x, f in zip(map(int, sb["length"].split(":")), (1, 1 / 60)))
    team = {t: {k: sum(p.get(k) or 0 for p in sb["players"] if p["team"] == t) for k in ("k", "gold", "dmg")}
            for t in {p["team"] for p in sb["players"]}}
    out = []
    for p in sb["players"]:
        t = team[p["team"]]
        rec = {"round": ri, "match": label, "team": p["team"], "role": p["role"], "player": p["player"], "gol_name": None,
               "champion": p["champion"], "win": g["winner"] == p["team"], "length": g.get("length"), "src": "leaguepedia"}
        rec |= {k: (float(p[k]) if p.get(k) is not None else None) for k in ("k", "d", "a", "cs", "gold", "vs", "wards", "dmg",
                                                                          "dmg_taken", "gd15", "csd15", "xpd15", "solo", "steals")}
        per_min = lambda v, n=1: round(v / mins, n) if v is not None else None
        rec |= {"csm": per_min(rec["cs"]), "gpm": per_min(rec["gold"], 0), "dpm": per_min(rec["dmg"], 0), "vspm": per_min(rec["vs"], 2),
                "kp": round((rec["k"] + rec["a"]) / t["k"] * 100, 1) if t["k"] else None,
                "gold_pct": round(rec["gold"] / t["gold"] * 100, 1) if rec["gold"] is not None and t["gold"] else None,
                "dmg_pct": round(rec["dmg"] / t["dmg"] * 100, 1) if rec["dmg"] is not None and t["dmg"] else None}
        out.append(rec)
    return out


def main(data_dir, cache, scoreboards=None):
    os.makedirs(cache, exist_ok=True)
    wpath = f"{data_dir}/worlds.json"
    w = json.load(open(wpath))
    rosters = {t["team"]: t for t in json.load(open(f"{data_dir}/rosters.json"))}
    # Leaguepedia scoreboards for games gol.gg can't serve, keyed by match label ("MKOI vs T1 G1")
    sbs = {}
    for path in scoreboards or []:
        sbs |= {x["match"]: x for x in json.load(open(path))["games"]}
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
                    if label in sbs:
                        out += from_scoreboard(sbs[label], ri, label, g)
                        print(f"{label}: Leaguepedia scoreboard", file=sys.stderr)
                    else:
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
                    for key in BAD.get((label, rec["player"]), []):
                        rec[key] = None
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
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
