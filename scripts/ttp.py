"""Collect each starter's solo-queue accounts from trackingthepros.com.

usage: python3 -I ttp.py rosters.json out.json
"""
import html, json, re, subprocess, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"
ROLES = ["top", "jungle", "mid", "bot", "support"]
ACCT_RE = re.compile(r"<tr( class='inactive_account')?\s*><td><b>\[([A-Z]+)\]</b>\s*(.*?)</td><td class='dt-right'>(.*?)</td></tr>")


def get(url):
    return subprocess.run(["curl", "-s", "-L", "--max-time", "30", "-A", UA, url], capture_output=True, text=True).stdout


def player(nick):
    page = get("https://www.trackingthepros.com/player/" + urllib.parse.quote(nick.replace(" ", "_")))
    team = re.search(r"<td>Team</td><td class='dt-right'>(?:<a [^>]*>)?([^<]*)", page)
    role = re.search(r"<td>Role</td><td class='dt-right'>([^<]*)", page)
    accts = [{"region": r, "riot_id": html.unescape(name).strip(), "rank": html.unescape(rank).strip(),
              "active": not inactive} for inactive, r, name, rank in ACCT_RE.findall(page)]
    return {"ttp_team": team.group(1).strip() if team else None, "ttp_role": role.group(1).strip() if role else None,
            "accounts": accts}


def main(roster_path, out_path):
    rosters = json.load(open(roster_path))
    jobs = [(t["team"], t["full"], role, t[role]) for t in rosters for role in ROLES]
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: player(j[3]), jobs))
    out = []
    for (team, full, role, nick), r in zip(jobs, res):
        out.append({"team": team, "full": full, "role": role, "player": nick, **r})
        krna = [a for a in r["accounts"] if a["region"] in ("KR", "NA")]
        print(f"{team:5} {nick:12} ttp_team={r['ttp_team']!s:28} accts={len(r['accounts'])} "
              f"KR/NA active={sum(a['active'] for a in krna)} all={len(krna)}", file=sys.stderr)
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
