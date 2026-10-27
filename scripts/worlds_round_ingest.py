"""Fold a finished Swiss round (results + drafts) and the next round's schedule/odds into data/worlds.json.

Input JSON (one collection pass):
  {"collected", "round2": [{a, b, winner, kills, length, blue, red, first_pick, src, bans, picks}],
   "standings", "round3": {date, note, matches: [{pool, a, b, format, time_tw, time_ct, pct, poly, kalshi}]},
   "outright": {label, poly: {team: %}, kalshi?: {team: %}},
   "advance": {market: {team: [ko, 3-0, 0-3]}, model: {team: [3-0, 3-1, 3-2, adv]} | null}}
The finished round's match prices at upcoming time become `pre_pct`, so the prediction page can score them.

usage: python3 -I worlds_round_ingest.py data/worlds.json collected.json round_index
"""
import json, sys

path, src, ri = sys.argv[1], sys.argv[2], int(sys.argv[3])
w, d = json.load(open(path)), json.load(open(src))
done_key, next_key = f"round{ri + 1}", f"round{ri + 2}"

rnd = w["rounds"][ri]
res = {frozenset((m["a"], m["b"])): m for m in d[done_key]}
pre_when = rnd.get("note", "").split("Polymarket 價格為 ")[-1] if "Polymarket 價格為" in rnd.get("note", "") else ""
for m in rnd["matches"]:
    r = res[frozenset((m["a"], m["b"]))]
    flip = r["a"] != m["a"]   # keep our a/b order; kills follow it
    m["pre_pct"] = m.pop("pct")
    for k in ("poly", "kalshi", "time_ct"):
        m.pop(k, None)
    m.update(winner=r["winner"], kills=r["kills"][::-1] if flip else r["kills"], length=r["length"], blue=r["blue"], red=r["red"],
             first_pick=r["first_pick"], draft_source=r["src"], draft={"order_known": True, "bans": r["bans"], "picks": r["picks"]})
rnd["status"] = "done"
rnd["pre_label"] = f"Polymarket 賽前價格（{pre_when}）" if pre_when else "Polymarket 賽前價格"
rnd["note"] = rnd["note"].split("；Polymarket")[0]

w["standings"] = d["standings"]
nxt = d.get(next_key)
if nxt and nxt.get("matches"):
    for m in nxt["matches"]:
        if m.get("pct") and not m.get("poly"):
            m["poly"] = [round(100 / x, 2) for x in m["pct"]]
        m["kalshi"] = m.get("kalshi") or None
    fmts = sorted({m["format"] for m in nxt["matches"]})
    w["rounds"].append({"name": ["第一輪", "第二輪", "第三輪", "第四輪", "第五輪"][ri + 1], "status": "upcoming",
                        "format": " / ".join(fmts), "date": nxt["date"],
                        "note": "；".join(x for x in [nxt.get("note"), f"Polymarket 價格為 {d['outright']['label']}"] if x),
                        "matches": nxt["matches"]})

o = w["outright"]
o["now_label"] = d["outright"]["label"]
for r in o["rows"]:
    p = d["outright"]["poly"].get(r["team"])
    if p is not None:
        r["poly"], r["poly_odds"] = p, round(100 / p, 2) if p else None
    k = (d["outright"].get("kalshi") or {}).get(r["team"])
    if k is not None:
        r["kalshi"] = k
o["rows"].sort(key=lambda r: -r["poly"])

A, mk, md = w["advance"], d["advance"].get("market") or {}, d["advance"].get("model") or {}
for r in A["rows"]:
    if r["team"] in mk:
        r["ko"], r["x30"], r["x03"] = mk[r["team"]]
    if r["team"] in md:
        r["m30"], r["m31"], r["m32"], r["madv"] = md[r["team"]]
A["rows"].sort(key=lambda r: -(r["ko"] or 0))

w["collected"] = d["collected"]
json.dump(w, open(path, "w"), ensure_ascii=False, indent=1)
print("rounds:", [(r["name"], r["status"], len(r["matches"])) for r in w["rounds"]])
