"""Discover starters' NA accounts by crawling NA solo games: OP.GG tags known pros in each game's
participant list (summoner.player), so pros meeting each other in NA soloq reveal their accounts.

usage: python3 -I discover_na.py data_dir [hops]
writes data_dir/na_discovered.json
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soloq

SINCE = "2026-10-11"
PART_RE = re.compile(r'Participant\(Summoner\("((?:[^"\\]|\\.)*)",(Player\((.*?)\)|None|null|"[^"]*"),"((?:[^"\\]|\\.)*)"\),"([^"]*)","([^"]*)"\)')


def game_participants(game):
    text, err = soloq.call("lol_get_summoner_game_detail", {
        "game_id": game["id"], "region": "NA", "created_at": game["time"],
        "desired_output_fields": ["data.game_detail.teams[].participants[].summoner.{game_name,player,tagline}",
                                  "data.game_detail.teams[].participants[].{champion_name,position}"]})
    return [] if err else text


def parse_pros(text):
    """Return [(nickname, game_name, tagline)] for participants OP.GG tags as pro players."""
    header = dict(re.findall(r"class (\w+): ([\w,]+)", text))
    out = []
    # Player(...) fields come in the order the header declares
    pfields = header.get("Player", "").split(",")
    for m in re.finditer(r'Summoner\("((?:[^"\\]|\\.)*)",Player\(((?:"(?:[^"\\]|\\.)*"|[^()"])*)\),"((?:[^"\\]|\\.)*)"\)', text):
        vals = re.findall(r'"((?:[^"\\]|\\.)*)"|(null|None|-?\d+)', m.group(2))
        vals = [a if a or not b else b for a, b in vals]
        player = dict(zip(pfields, vals))
        out.append((player.get("nickname"), m.group(1), m.group(3)))
    return out


def main(data_dir, hops=2):
    raw = json.load(open(f"{data_dir}/soloq_raw.json"))
    rosters = json.load(open(f"{data_dir}/rosters.json"))
    starters = {t[r].lower(): (t["team"], r, t[r]) for t in rosters for r in soloq.ROLES}
    known = {}  # (game_name, tagline) lower -> nickname
    for p in raw:
        for a in p["accounts"]:
            if a["region"] == "NA":
                known[(a["game_name"].lower(), a["tagline"].lower())] = p["player"]
    seen_games, found = set(), {}
    frontier = [g for p in raw for g in p["games"] if g["account"].startswith("NA:") and g["time"][:10] >= SINCE]
    for hop in range(hops):
        frontier = [g for g in frontier if g["id"] not in seen_games]
        seen_games.update(g["id"] for g in frontier)
        print(f"hop {hop}: crawling {len(frontier)} games", file=sys.stderr)
        with ThreadPoolExecutor(6) as ex:
            texts = list(ex.map(game_participants, frontier))
        new_accts = []
        for text in texts:
            for nick, gn, tag in parse_pros(text or ""):
                if not nick or nick.lower() not in starters:
                    continue
                key = (gn.lower(), tag.lower())
                if key in known or key in found:
                    continue
                team, role, name = starters[nick.lower()]
                found[key] = {"team": team, "role": role, "player": name, "game_name": gn, "tagline": tag, "region": "NA"}
                new_accts.append(found[key])
                print(f"  found {team} {name}: {gn}#{tag}", file=sys.stderr)
        frontier = []
        for a in new_accts:
            frontier += [g for g in soloq.matches(a) if g["time"][:10] >= SINCE]
    json.dump(list(found.values()), open(f"{data_dir}/na_discovered.json", "w"), ensure_ascii=False, indent=1)
    print(f"discovered {len(found)} new NA accounts", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2)
