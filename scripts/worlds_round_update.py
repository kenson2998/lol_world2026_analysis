"""Fold results of a (possibly partly) played Swiss round into data/worlds.json; Bo3 matches keep a games list.

Input JSON:
  {"collected", "finished": [{a, b, winner, score, games: [{winner, kills, length, blue, red, first_pick, src, bans, picks}]}],
   "unfinished": [{a, b, pct, poly, kalshi}], "standings",
   "outright": {label, poly: {team: %}, kalshi?: {team: %}},
   "advance": {market: {team: [ko, 3-0, 0-3]}, model: {team: [3-0, 3-1, 3-2, adv]} | null},
   "next"?: {name, date, note, matches: [{pool, a, b, format, time_tw, time_ct, pct, poly, kalshi}]}}
A finished match's last upcoming price becomes `pre_pct`, so the prediction page can score it.
The round is "live" until every match has a winner, then "done".

usage: python3 -I worlds_round_update.py data/worlds.json collected.json round_index
"""
import json, sys

path, src, ri = sys.argv[1], sys.argv[2], int(sys.argv[3])
w, d = json.load(open(path)), json.load(open(src))
rnd = w["rounds"][ri]
by_pair = {frozenset((m["a"], m["b"])): m for m in rnd["matches"]}


def book_pct(books):
    """Bookmaker implied win chance for a/b: each book's 1/odds with its margin removed, averaged (same as the page)."""
    if not books:
        return None
    pa = sum((1 / b["odds"][0]) / (1 / b["odds"][0] + 1 / b["odds"][1]) for b in books) / len(books)
    return [round(pa * 100, 1), round((1 - pa) * 100, 1)]


def game(g, flip):
    return {"winner": g["winner"], "kills": g["kills"][::-1] if flip else g["kills"], "length": g["length"], "blue": g["blue"],
            "red": g["red"], "first_pick": g["first_pick"], "draft_source": g["src"],
            "draft": {"order_known": True, "bans": g["bans"], "picks": g["picks"]}} | ({"mvp": g["mvp"]} if g.get("mvp") else {})


for r in d["finished"]:
    m = by_pair[frozenset((r["a"], r["b"]))]
    if m.get("winner"):
        continue
    flip = r["a"] != m["a"]   # keep our a/b order; kills and score follow it
    m["pre_pct"] = m.pop("pct", None) or book_pct(m.get("books"))
    for k in ("poly", "kalshi"):
        m.pop(k, None)
    games = [game(g, flip) for g in r["games"]]
    m["winner"] = r["winner"]
    if len(games) == 1 and m.get("format", "Bo1") == "Bo1":
        m.update(games[0])
    else:
        m["score"] = r["score"][::-1] if flip else r["score"]
        m["games"] = games

for r in d.get("unfinished", []):
    m = by_pair[frozenset((r["a"], r["b"]))]
    flip = r["a"] != m["a"]
    for k in ("pct", "poly", "kalshi"):
        if r.get(k):
            m[k] = r[k][::-1] if flip else r[k]
    if r.get("books"):   # fresher bookmaker lines replace the old ones
        m["books"] = [b | {"odds": b["odds"][::-1] if flip else b["odds"]} for b in r["books"]]

rnd["status"] = "done" if all(m.get("winner") for m in rnd["matches"]) else "live"
when = rnd.get("note", "").split("Polymarket 價格為 ")[-1] if "Polymarket 價格為" in rnd.get("note", "") else ""
rnd["pre_label"] = f"Polymarket 賽前價格（{when}）" if when else "Polymarket 賽前價格"
w["standings"] = d["standings"]

nxt = d.get("next")
if nxt and nxt.get("matches") and not any(r["name"] == nxt["name"] for r in w["rounds"]):
    for m in nxt["matches"]:
        if m.get("pct") and not m.get("poly"):
            m["poly"] = [round(100 / x, 2) for x in m["pct"]]
    priced = any(m.get("pct") for m in nxt["matches"])
    w["rounds"].append({"name": nxt["name"], "status": "upcoming", "format": " / ".join(sorted({m["format"] for m in nxt["matches"]})),
                        "date": nxt["date"], "note": "；".join(x for x in [nxt.get("note"),
                            f"Polymarket 價格為 {d['outright']['label']}" if priced else "尚未取得賠率"] if x),
                        "matches": nxt["matches"]})

o = w["outright"]
if d["outright"].get("poly"):   # no market snapshot this time: keep the previous prices and their label
    o["now_label"] = d["outright"]["label"]
for r in o["rows"] if d["outright"].get("poly") else []:
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
print("rounds:", [(r["name"], r["status"], sum(bool(m.get("winner")) for m in r["matches"]), len(r["matches"])) for r in w["rounds"]])
