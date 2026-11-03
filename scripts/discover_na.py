"""Discover starters' NA accounts by crawling NA solo games: OP.GG tags known pros in each game's
participant list (summoner.player), so pros meeting each other in NA soloq reveal their accounts.

usage: python3 -I discover_na.py data_dir [hops]
writes data_dir/na_discovered.json
"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soloq

SINCE = os.environ.get("SINCE", "2026-10-11")   # only crawl games from this date on (KST date)
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
    # Summoner(...) and Player(...) fields come in the order the header declares (OP.GG has changed it before:
    # game_name,player,tagline then game_name,tagline,player), so read them by name rather than by position
    sfields, pfields = header.get("Summoner", "").split(","), header.get("Player", "").split(",")
    arg = r'"(?:[^"\\]|\\.)*"|Player\((?:"(?:[^"\\]|\\.)*"|[^()"])*\)|null|None'
    for m in re.finditer(rf'Summoner\(((?:(?:{arg}),?)+)\)', text):
        parts = re.findall(arg, m.group(1))
        summ = dict(zip(sfields, parts))
        p = summ.get("player", "")
        if not p.startswith("Player("):
            continue
        vals = re.findall(r'"((?:[^"\\]|\\.)*)"|(null|None|-?\d+)', p[7:-1])
        player = dict(zip(pfields, [a if a or not b else b for a, b in vals]))
        unq = lambda s: (s or "")[1:-1] if (s or "").startswith('"') else ""
        out.append((player.get("nickname"), unq(summ.get("game_name")), unq(summ.get("tagline"))))
    return out


def main(data_dir, hops=2):
    raw = json.load(open(f"{data_dir}/soloq_raw.json"))
    # the latest window pull (soloq_na_window.py) seeds the crawl too: its games are the freshest NA ones
    win = json.load(open(f"{data_dir}/soloq_na.json"))["players"] if os.path.exists(f"{data_dir}/soloq_na.json") else []
    rosters = json.load(open(f"{data_dir}/rosters.json"))
    starters = {t[r].lower(): (t["team"], r, t[r]) for t in rosters for r in soloq.ROLES}
    known = {}  # (game_name, tagline) lower -> nickname
    for p in raw:
        for a in p["accounts"]:
            if a["region"] == "NA":
                known[(a["game_name"].lower(), a["tagline"].lower())] = p["player"]
    for p in win:
        for rid in p["accounts"]:
            gn, tag = rid.rsplit("#", 1)
            known[(gn.lower(), tag.lower())] = p["player"]
    seen_games, found = set(), {}
    frontier = [g for p in raw + win for g in p["games"] if g["account"].startswith("NA:") and g["time"][:10] >= SINCE]
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
