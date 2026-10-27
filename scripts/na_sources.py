"""Collect Worlds 2026 NA bootcamp accounts from TrackingThePros' bootcamp tracker and AussyELO's tracker,
plus accounts found by discover_na.py, mapped onto our rosters.

usage: python3 -I na_sources.py data_dir
writes data_dir/na_bootcamp.json
"""
import html, json, os, re, subprocess, sys, urllib.parse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"
ROLES = ["top", "jungle", "mid", "bot", "support"]


def get(url, *headers):
    cmd = ["curl", "-s", "-L", "--max-time", "30", "-A", UA]
    for h in headers:
        cmd += ["-H", h]
    return subprocess.run(cmd + [url], capture_output=True, text=True).stdout


def ttp_bootcamp():
    raw = get("https://www.trackingthepros.com/d/list_bootcamp", "X-Requested-With: XMLHttpRequest",
              "Referer: https://www.trackingthepros.com/bootcamp")
    out = []
    for row in json.loads(raw)["data"]:
        nick = re.sub(r"<[^>]+>", "", row["player"]).strip()
        m = re.search(r"/summoners/NA/([^'\"]+)'", row["summoner"])
        if not m:
            continue
        # op.gg slug is "<game name>-<tag>"; the tag never contains '-'
        name, tag = html.unescape(urllib.parse.unquote(m.group(1))).rsplit("-", 1)
        out.append({"player": nick, "game_name": name, "tagline": tag, "source": "ttp-bootcamp"})
    return out


def aussyelo():
    page = get("https://www.aussyelo.com/tracking-the-pros")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)))
    text = re.sub(r"(\s*\|\s*)+", " | ", text)
    # rows look like: | 18 | HS | Hans Sama | G2 | / | ADC | Hans von melzer | #1234 | NEW BOOTCAMP |
    rows = re.findall(r"\| \d{2} \| \w{2} \| ([^|]+?) \| (\w+) \| / \| \w+ \| ([^|]+?) \| #([^|]+?) \|", text)
    return [{"player": html.unescape(p), "game_name": html.unescape(n), "tagline": html.unescape(t), "source": "aussyelo"}
            for p, _team, n, t in rows]


def main(data_dir):
    rosters = json.load(open(f"{data_dir}/rosters.json"))
    starters = {t[r].lower(): (t["team"], r, t[r]) for t in rosters for r in ROLES}
    found = ttp_bootcamp() + aussyelo()
    disc = f"{data_dir}/na_discovered.json"
    if os.path.exists(disc):
        found += [dict(a, source="opgg-tag") for a in json.load(open(disc))]
    out, seen = [], set()
    for a in found:
        hit = starters.get(a["player"].lower())
        key = (a["game_name"].lower(), a["tagline"].lower())
        if not hit or key in seen:
            continue
        seen.add(key)
        team, role, name = hit
        out.append({"team": team, "role": role, "player": name, "region": "NA",
                    "riot_id": f'{a["game_name"]}#{a["tagline"]}', "source": a["source"]})
    json.dump(out, open(f"{data_dir}/na_bootcamp.json", "w"), ensure_ascii=False, indent=1)
    for a in out:
        print(f'{a["team"]:5} {a["player"]:12} {a["riot_id"]:28} {a["source"]}', file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
