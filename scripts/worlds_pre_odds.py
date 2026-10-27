"""Copy pre-game Polymarket match prices for Round 1 (from the earlier odds.json snapshot) into worlds.json,
so the prediction page can score market favourites against results.

usage: python3 -I worlds_pre_odds.py data_dir
"""
import json, re, sys

data_dir = sys.argv[1]
odds = json.load(open(f"{data_dir}/odds.json"))
w = json.load(open(f"{data_dir}/worlds.json"))
pre = {}
for r in odds["round1"]:
    cents = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)¢", r["cents"])]
    pre[frozenset((r["a"], r["b"]))] = {r["a"]: cents[0], r["b"]: cents[1]}
for m in w["rounds"][0]["matches"]:
    p = pre.get(frozenset((m["a"], m["b"])))
    if p:
        m["pre_pct"] = [p[m["a"]], p[m["b"]]]
w["rounds"][0]["pre_label"] = f"Polymarket 賽前價格（{odds['collected']} 前後快照）"
json.dump(w, open(f"{data_dir}/worlds.json", "w"), ensure_ascii=False, indent=1)
print([(m["a"], m["b"], m.get("pre_pct"), m["winner"]) for m in w["rounds"][0]["matches"]])
