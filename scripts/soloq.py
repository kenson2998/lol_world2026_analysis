"""Pull each Worlds 2026 starter's last 20 solo-queue games (KR + NA) from the public OP.GG MCP API
and aggregate champion usage / win rate per team and position.

usage: python3 -I soloq.py rosters.json out_dir
"""
import json, os, re, subprocess, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

MCP = "https://mcp-api.op.gg/mcp"
REGIONS = ["KR", "NA"]
N_GAMES = 20
ROLES = ["top", "jungle", "mid", "bot", "support"]


def call(tool, args, retries=3):
    # curl rather than urllib: the conda python here is built without ssl
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}})
    cmd = ["curl", "-s", "--max-time", "60", "-X", "POST", MCP, "-H", "Content-Type: application/json",
           "-H", "Accept: application/json, text/event-stream", "--data-binary", "@-"]
    err = None
    for i in range(retries):
        try:
            raw = subprocess.run(cmd, input=body, capture_output=True, text=True, check=True).stdout
            res = json.loads(raw[raw.find("{"):])["result"]
            return res["content"][0]["text"], res.get("isError", False)
        except Exception as e:
            err = e
            time.sleep(2 * (i + 1))
    return f"ERROR {err}", True


def lookup(nick, region):
    text, is_err = call("lol_get_pro_player_riot_id", {"player_name": nick, "region": region})
    if is_err:
        return None
    try:
        p = json.loads(text)["data"]["player"]
    except (ValueError, KeyError, TypeError):
        return None
    if not p:
        return None
    names = {a.lower() for a in [p.get("nickname") or ""] + (p.get("aliases") or [])}
    if nick.lower() not in names:
        return None  # fuzzy match to a different player
    rid = p["riot_id"]
    return {"game_name": rid["game_name"], "tagline": rid["tagline"], "region": region,
            "opgg_team": (p.get("team") or {}).get("short_name")}


GAME_RE = re.compile(r'GameHistory\("([^"]*)","([^"]*)","([^"]*)",\[Participant\(Summoner\("(?:[^"\\]|\\.)*"\),'
                     r'"([^"]*)","([^"]*)",Stats\("([^"]*)"\)\)\]\)')


def matches(acc):
    text, is_err = call("lol_list_summoner_matches", {
        "game_name": acc["game_name"], "tag_line": acc["tagline"], "region": acc["region"], "limit": N_GAMES,
        "desired_output_fields": ["data.game_history[].{created_at,game_type,id}",
                                  "data.game_history[].participants[].{champion_name,position}",
                                  "data.game_history[].participants[].stats.{result}",
                                  "data.game_history[].participants[].summoner.{game_name}"]})
    if is_err:
        return []
    return [{"id": m[0], "time": m[1], "queue": m[2], "champion": m[3], "position": m[4], "result": m[5],
             "account": f'{acc["region"]}:{acc["game_name"]}#{acc["tagline"]}'} for m in GAME_RE.findall(text)]


def usable(acc):
    # deleted / flagged accounts carry placeholder names that no longer resolve
    return not re.search(r"del$|^FLAGGED", acc["game_name"])


def player_games(nick, ttp_accounts=()):
    accounts = [a for a in (lookup(nick, r) for r in REGIONS) if a]
    for a in ttp_accounts:
        if a["region"] in REGIONS and "#" in a["riot_id"]:
            name, tag = a["riot_id"].rsplit("#", 1)
            accounts.append({"game_name": name.strip(), "tagline": tag.strip(), "region": a["region"], "source": "ttp"})
    seen, accounts = set(), [a for a in accounts if usable(a)]
    accounts = [a for a in accounts
                if (k := (a["region"], a["game_name"].lower(), a["tagline"].lower())) not in seen and not seen.add(k)]
    games = []
    for acc in accounts:
        found = matches(acc)
        acc["games_seen"] = len(found)
        games += found
    accounts = [a for a in accounts if a["games_seen"]]
    # remakes come back as neither WIN nor LOSE; drop them
    solo = [g for g in games if g["queue"] == "SOLORANKED" and g["result"] in ("WIN", "LOSE")]
    # keep every solo game; build_report drops off-role / out-of-window games before taking the newest N_GAMES
    solo = sorted({g["id"]: g for g in solo}.values(), key=lambda g: g["time"], reverse=True)
    return accounts, solo


def summarize(games):
    n = len(games)
    champs = defaultdict(lambda: [0, 0])
    for g in games:
        champs[g["champion"]][0] += 1
        champs[g["champion"]][1] += g["result"] == "WIN"
    rows = [{"champion": c, "games": k, "wins": w, "pick_rate": round(k / n * 100, 1),
             "win_rate": round(w / k * 100, 1)} for c, (k, w) in champs.items()]
    rows.sort(key=lambda r: (-r["games"], -r["win_rate"], r["champion"]))
    wins = sum(g["result"] == "WIN" for g in games)
    return {"games": n, "wins": wins, "win_rate": round(wins / n * 100, 1) if n else None,
            "first": games[-1]["time"] if n else None, "last": games[0]["time"] if n else None,
            "positions": dict(Counter(g["position"] for g in games).most_common()), "champions": rows}


def main(roster_path, out_dir):
    rosters = json.load(open(roster_path))
    ttp = {(p["team"], p["role"]): p for p in json.load(open(f"{out_dir}/ttp_accounts.json"))}
    # NA bootcamp trackers (na_sources.py) and hand-entered accounts add the NA IDs Riot handed out for Worlds
    for extra in ("na_bootcamp.json", "na_manual.json"):
        if os.path.exists(f"{out_dir}/{extra}"):
            for a in json.load(open(f"{out_dir}/{extra}")):
                ttp[(a["team"], a["role"])]["accounts"].append({"region": "NA", "riot_id": a["riot_id"]})
    # OP.GG's pro lookup fails now and then; keep every account that has produced games before
    cache_path = f"{out_dir}/known_accounts.json"
    known = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    for key, accts in known.items():
        team, role = key.split("/")
        if (team, role) in ttp:
            ttp[(team, role)]["accounts"] += [{"region": a["region"], "riot_id": f'{a["game_name"]}#{a["tagline"]}'} for a in accts]
    jobs = [(t["team"], t["full"], role, t[role]) for t in rosters for role in ROLES]
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda j: player_games(j[3], ttp[(j[0], j[2])]["accounts"]), jobs))
    out = []
    for (team, full, role, nick), (accounts, games) in zip(jobs, results):
        ttp_team = ttp[(team, role)]["ttp_team"]
        out.append({"team": team, "role": role, "player": nick, "accounts": accounts,
                    "ttp_team": ttp_team, "team_mismatch": bool(ttp_team) and ttp_team.lower() not in full.lower()
                    and full.lower() not in ttp_team.lower(),
                    "summary": summarize(games), "games": games})
        print(f"{team:6} {role:8} {nick:12} accts={len(accounts)} solo={len(games)}", file=sys.stderr)
    json.dump(out, open(f"{out_dir}/soloq_raw.json", "w"), ensure_ascii=False, indent=1)
    for p in out:
        seen = {(a["region"], a["game_name"].lower(), a["tagline"].lower()) for a in known.get(f'{p["team"]}/{p["role"]}', [])}
        known.setdefault(f'{p["team"]}/{p["role"]}', []).extend(
            {"region": a["region"], "game_name": a["game_name"], "tagline": a["tagline"]} for a in p["accounts"]
            if (a["region"], a["game_name"].lower(), a["tagline"].lower()) not in seen)
    json.dump(known, open(cache_path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
