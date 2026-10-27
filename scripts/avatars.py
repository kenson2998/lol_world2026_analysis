"""Build "TEAM/player" -> data-URI headshot map from the LoL Esports API (inlined, the report can't load remote images).

usage: python3 -I avatars.py data_dir [cache_dir]
writes data_dir/player_avatars.json
"""
import base64, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

API = "https://esports-api.lolesports.com/persisted/gw/getTeams?hl=en-US"
KEY = "x-api-key: 0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"  # public key the lolesports.com site ships
ROLES = ["top", "jungle", "mid", "bot", "support"]
SIZE = "156"  # shown at 52px; 3x keeps it sharp on high-DPI screens
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def main(data_dir, cache):
    os.makedirs(cache, exist_ok=True)
    teams = json.loads(subprocess.run(["curl", "-s", "--max-time", "60", "-H", KEY, API],
                                      capture_output=True, text=True, check=True).stdout)["data"]["teams"]
    by_name = {}
    for t in teams:
        if t.get("status") == "active":
            for k in {norm(t["name"]), norm(t["code"])}:
                by_name.setdefault(k, []).append(t)
    rosters = json.load(open(f"{data_dir}/rosters.json"))
    jobs = []
    for r in rosters:
        # academy sides share names/codes (LYON vs Lyon Academy): pick the one holding most of our starters
        ours = {norm(r[role]) for role in ROLES}
        cands = by_name.get(norm(r["full"]), []) + by_name.get(norm(r["team"]), [])
        team = max(cands, key=lambda t: len(ours & {norm(p["summonerName"]) for p in t["players"]}), default=None)
        players = {norm(p["summonerName"]): p for p in (team or {}).get("players", [])}
        for role in ROLES:
            p = players.get(norm(r[role]))
            img = (p or {}).get("image", "")
            if img and "default-headshot" not in img:
                jobs.append((f'{r["team"]}/{r[role]}', img.replace("http://", "https://")))
            else:
                print(f'no headshot: {r["team"]} {r[role]} (team match: {bool(team)})', file=sys.stderr)

    def fetch(job):
        key, url = job
        src = os.path.join(cache, norm(key) + os.path.splitext(url)[1].lower())
        small = os.path.join(cache, norm(key) + f"_{SIZE}.png")
        if not os.path.exists(small):
            if not os.path.exists(src):
                subprocess.run(["curl", "-s", "--max-time", "60", "-o", src, url], check=True)
            # headshots are wide half-body shots: crop a top-centred square (head + shoulders) before scaling
            info = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", src], capture_output=True, text=True).stdout
            w, h = (int(re.search(rf"{k}: (\d+)", info).group(1)) for k in ("pixelWidth", "pixelHeight"))
            side = min(w, int(h * 0.8))
            subprocess.run(["sips", "-s", "format", "png", "-c", str(side), str(side), "--cropOffset", "0", str((w - side) // 2),
                            src, "--out", small], capture_output=True, check=True)
            subprocess.run(["sips", "-Z", SIZE, small], capture_output=True, check=True)
        return key, "data:image/png;base64," + base64.b64encode(open(small, "rb").read()).decode()

    with ThreadPoolExecutor(8) as ex:
        avatars = dict(ex.map(fetch, jobs))
    json.dump(avatars, open(f"{data_dir}/player_avatars.json", "w"))
    print(f"{len(avatars)} headshots", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(sys.argv[1], ".avatar_cache"))
