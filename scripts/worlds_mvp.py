"""Set each game's MVP (Player of the Game) in data/worlds.json, matched by gol.gg game id.

Input JSON: {"games": [{"gol": 83638, "mvp": "Canyon" | null, ...}]}; null leaves the game without an MVP.
usage: python3 -I worlds_mvp.py data/worlds.json mvps.json
"""
import json, re, sys

path, src = sys.argv[1], sys.argv[2]
w = json.load(open(path))
mvp = {g["gol"]: g["mvp"] for g in json.load(open(src))["games"] if g.get("mvp")}
n = 0
for r in w["rounds"]:
    for m in r["matches"]:
        for g in m.get("games") or ([m] if m.get("winner") else []):
            gid = re.search(r"/stats/(\d+)/", g.get("draft_source", ""))
            name = gid and mvp.get(int(gid.group(1)))
            if not name:
                continue
            if name not in {p["player"] for p in g["draft"]["picks"]}:
                sys.exit(f"{name} did not play gol {gid.group(1)}")
            g["mvp"] = name
            n += 1
json.dump(w, open(path, "w"), ensure_ascii=False, indent=1)
print(f"{n} games with MVP")
