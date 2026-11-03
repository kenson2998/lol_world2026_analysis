"""NA + KR solo-queue practice of the teams still in the event, over a Taiwan-date window, from the public OP.GG MCP API.

Accounts come from the same places as soloq.py: OP.GG's pro lookup, TrackingThePros / bootcamp trackers
(ttp_accounts.json, na_bootcamp.json, which also merges discover_na.py finds), hand-entered ones (na_manual.json)
and every account seen before (known_accounts.json). Ranked solo games on either server inside the window are kept,
each tagged with its server (remakes dropped). New accounts that produced games are added to known_accounts.json.

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
    """NA and KR accounts (riot ids) known for a starter, from every source soloq.py uses."""
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
    return [a for a in out if a["region"] in soloq.REGIONS]


def main(data_dir, roster_path, start, end, teams):
    rosters = {t["team"]: t for t in json.load(open(roster_path))}
    lo, hi = start, end
    jobs = [(t, role, rosters[t][role]) for t in teams for role in soloq.ROLES]

    def run(job):
        team, role, nick = job
        accts, games = soloq.player_games(nick, accounts_for(data_dir, team, role))
        keep = []
        for g in games:
            t = tw_time(g["time"])
            if lo <= t.strftime("%Y-%m-%d") <= hi:
                keep.append(g | {"region": g["account"].split(":")[0], "time_tw": t.strftime("%m/%d %H:%M"),
                                 "on_role": POS_ROLE.get(g["position"]) == role})
        last = max((tw_time(g["time"]) for g in games), default=None)
        last_na = max((tw_time(g["time"]) for g in games if g["account"].startswith("NA:")), default=None)
        # an account that returned the full 20 with its oldest game still inside the window may hold more games there
        acct_key = lambda a: f'{a["region"]}:{a["game_name"]}#{a["tagline"]}'
        partial = any(a["games_seen"] >= soloq.N_GAMES and min(tw_time(g["time"]) for g in games
                      if g["account"] == acct_key(a)).strftime("%Y-%m-%d") >= lo
                      for a in accts if any(g["account"] == acct_key(a) for g in games))
        return {"team": team, "role": role, "player": nick, "partial": partial,
                # NA ids stay in "accounts" (as before); every account with its server in "all_accounts"
                "accounts": [f'{a["game_name"]}#{a["tagline"]}' for a in accts if a["region"] == "NA"],
                "all_accounts": [acct_key(a) for a in accts],
                "games": keep, "summary": soloq.summarize(keep),
                "on_role": sum(g["on_role"] for g in keep),
                "last": last.strftime("%m/%d %H:%M") if last else None,
                "last_region": next((g["account"].split(":")[0] for g in games if tw_time(g["time"]) == last), None),
                "last_na": last_na.strftime("%m/%d %H:%M") if last_na else None}

    with ThreadPoolExecutor(6) as ex:
        players = list(ex.map(run, jobs))
    for p in players:
        by = {r: sum(g["region"] == r for g in p["games"]) for r in soloq.REGIONS}
        print(f'{p["team"]:5} {p["role"]:8} {p["player"]:12} accts={len(p["all_accounts"])} games={by} last={p["last"]} {p["last_region"]}', file=sys.stderr)
    # remember every account that produced games, so the next pull keeps it even if a lookup fails
    kpath = f"{data_dir}/known_accounts.json"
    known = json.load(open(kpath)) if os.path.exists(kpath) else {}
    for p in players:
        have = {(a["region"], a["game_name"].lower(), a["tagline"].lower()) for a in known.get(f'{p["team"]}/{p["role"]}', [])}
        for key in p["all_accounts"]:
            region, rid = key.split(":", 1)
            gn, tag = rid.rsplit("#", 1)
            if (region, gn.lower(), tag.lower()) not in have:
                known.setdefault(f'{p["team"]}/{p["role"]}', []).append({"region": region, "game_name": gn, "tagline": tag})
                print(f'  new account {p["team"]} {p["player"]}: {key}', file=sys.stderr)
    json.dump(known, open(kpath, "w"), ensure_ascii=False, indent=1)
    fetched = datetime.now(TW).strftime("%Y-%m-%d %H:%M")
    json.dump({"window": [lo, hi], "fetched": fetched, "teams": teams, "players": players},
              open(f"{data_dir}/soloq_na.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
