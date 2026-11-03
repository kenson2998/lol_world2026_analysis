"""NA solo-queue practice of the teams still in the event, over a Taiwan-date window, from the public OP.GG MCP API.

Accounts come from the same places as soloq.py: OP.GG's pro lookup, TrackingThePros / bootcamp trackers
(ttp_accounts.json, na_bootcamp.json), hand-entered ones (na_manual.json) and every account seen before
(known_accounts.json). Only NA ranked solo games inside the window are kept (remakes dropped).

usage: python3 -I soloq_na_window.py data_dir rosters.json YYYY-MM-DD YYYY-MM-DD TEAM [TEAM ...]
writes data_dir/soloq_na.json
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soloq

# OP.GG returns at most the latest 20 games per account (a larger limit is an error); a player whose account's 20 games
# all fall inside the window may have played more there, and is flagged `partial`
TW, KST = timezone(timedelta(hours=8)), timezone(timedelta(hours=9))
POS_ROLE = {"TOP": "top", "JUNGLE": "jungle", "MID": "mid", "ADC": "bot", "SUPPORT": "support"}


def tw_time(t):
    """OP.GG created_at is KST ("YYYY-MM-DDTHH:MM:SS..."); return it as a Taiwan-time datetime."""
    return datetime.fromisoformat(t[:19]).replace(tzinfo=KST).astimezone(TW)


def accounts_for(data_dir, team, role):
    """NA accounts (riot ids) known for a starter, from every source soloq.py uses."""
    out = []
    ttp = {(p["team"], p["role"]): p for p in json.load(open(f"{data_dir}/ttp_accounts.json"))}
    out += [a for a in ttp.get((team, role), {}).get("accounts", [])]
    for extra in ("na_bootcamp.json", "na_manual.json"):
        if os.path.exists(f"{data_dir}/{extra}"):
            out += [{"region": "NA", "riot_id": a["riot_id"]} for a in json.load(open(f"{data_dir}/{extra}"))
                    if a["team"] == team and a["role"] == role]
    if os.path.exists(f"{data_dir}/known_accounts.json"):
        out += [{"region": a["region"], "riot_id": f'{a["game_name"]}#{a["tagline"]}'}
                for a in json.load(open(f"{data_dir}/known_accounts.json")).get(f"{team}/{role}", [])]
    return [a for a in out if a["region"] == "NA"]


def main(data_dir, roster_path, start, end, teams):
    rosters = {t["team"]: t for t in json.load(open(roster_path))}
    lo, hi = start, end
    jobs = [(t, role, rosters[t][role]) for t in teams for role in soloq.ROLES]

    def run(job):
        team, role, nick = job
        accts, games = soloq.player_games(nick, accounts_for(data_dir, team, role))
        na = [a for a in accts if a["region"] == "NA"]
        keep = []
        for g in games:
            if not g["account"].startswith("NA:"):
                continue
            t = tw_time(g["time"])
            if lo <= t.strftime("%Y-%m-%d") <= hi:
                keep.append(g | {"time_tw": t.strftime("%m/%d %H:%M"), "on_role": POS_ROLE.get(g["position"]) == role})
        last_na = max((tw_time(g["time"]) for g in games if g["account"].startswith("NA:")), default=None)
        # an account that returned the full 20 with its oldest game still inside the window may hold more games there
        partial = any(a["games_seen"] >= soloq.N_GAMES and min(tw_time(g["time"]) for g in games
                      if g["account"] == f'NA:{a["game_name"]}#{a["tagline"]}').strftime("%Y-%m-%d") >= lo
                      for a in na if any(g["account"] == f'NA:{a["game_name"]}#{a["tagline"]}' for g in games))
        return {"team": team, "role": role, "player": nick, "partial": partial,
                "accounts": [f'{a["game_name"]}#{a["tagline"]}' for a in na],
                "games": keep, "summary": soloq.summarize(keep),
                "on_role": sum(g["on_role"] for g in keep),
                "last_na": last_na.strftime("%m/%d %H:%M") if last_na else None}

    with ThreadPoolExecutor(6) as ex:
        players = list(ex.map(run, jobs))
    for p in players:
        print(f'{p["team"]:5} {p["role"]:8} {p["player"]:12} NA accts={len(p["accounts"])} games={p["summary"]["games"]} last={p["last_na"]}', file=sys.stderr)
    fetched = datetime.now(TW).strftime("%Y-%m-%d %H:%M")
    json.dump({"window": [lo, hi], "fetched": fetched, "teams": teams, "players": players},
              open(f"{data_dir}/soloq_na.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
