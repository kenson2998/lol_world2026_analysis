"""One-off: fold Round 1 drafts (gol.gg / Liquipedia), Swiss record odds (Polymarket / Outdrafted) and
Polymarket title-price history into data/worlds.json.

usage: python3 -I worlds_r1_ingest.py data/worlds.json
"""
import json, sys

path = sys.argv[1]
w = json.load(open(path))


def P(n, team, champ, player, role):
    return {"n": n, "team": team, "champion": champ, "player": player, "role": role}


drafts = {
 ("GEN", "IG"): dict(blue="IG", red="GEN", first_pick="GEN",
   bans={"GEN": ["Nocturne", "Syndra", "Galio", "Lulu", "Ezreal"], "IG": ["Vi", "Lee Sin", "Cassiopeia", "Renata Glasc", "Lucian"]},
   picks=[P(1, "GEN", "Qiyana", "Canyon", "jungle"), P(2, "IG", "Jarvan IV", "Wei", "jungle"), P(3, "IG", "Rumble", "TheShy", "top"),
          P(4, "GEN", "Ornn", "Kiin", "top"), P(5, "GEN", "Akali", "Chovy", "mid"), P(6, "IG", "Aurora", "Rookie", "mid"),
          P(7, "IG", "Jhin", "JiaQi", "bot"), P(8, "GEN", "Corki", "Ruler", "bot"), P(9, "GEN", "Nautilus", "Duro", "support"),
          P(10, "IG", "Alistar", "Meiko", "support")], src="https://gol.gg/game/stats/83638/page-game/"),
 ("HLE", "TES"): dict(blue="TES", red="HLE", first_pick="HLE",
   bans={"HLE": ["Cassiopeia", "Qiyana", "Akali", "Corki", "Renekton"], "TES": ["Olaf", "Vi", "Jayce", "Nautilus", "Bard"]},
   picks=[P(1, "HLE", "Nocturne", "Kanavi", "jungle"), P(2, "TES", "Orianna", "Creme", "mid"), P(3, "TES", "Lee Sin", "Tian", "jungle"),
          P(4, "HLE", "Locke", "Zeka", "mid"), P(5, "HLE", "Jhin", "Gumayusi", "bot"), P(6, "TES", "Alistar", "Zhuo", "support"),
          P(7, "TES", "Ezreal", "JackeyLove", "bot"), P(8, "HLE", "Shen", "Delight", "support"), P(9, "HLE", "Ambessa", "Zeus", "top"),
          P(10, "TES", "K'Sante", "369", "top")], src="https://gol.gg/game/stats/83642/page-game/"),
 ("BLG", "MKOI"): dict(blue="MKOI", red="BLG", first_pick="BLG",
   bans={"BLG": ["Galio", "Nocturne", "Qiyana", "Twisted Fate", "Olaf"], "MKOI": ["Vi", "Rumble", "Cassiopeia", "Lee Sin", "Skarner"]},
   picks=[P(1, "BLG", "Seraphine", "ON", "support"), P(2, "MKOI", "Jarvan IV", "Elyoya", "jungle"), P(3, "MKOI", "Ezreal", "Supa", "bot"),
          P(4, "BLG", "Ashe", "Viper", "bot"), P(5, "BLG", "Akali", "Knight", "mid"), P(6, "MKOI", "Karma", "Alvaro", "support"),
          P(7, "MKOI", "Sylas", "Jojopyun", "mid"), P(8, "BLG", "Pantheon", "Xun", "jungle"), P(9, "BLG", "Ambessa", "Bin", "top"),
          P(10, "MKOI", "Renekton", "Myrwn", "top")], src="https://gol.gg/game/stats/83645/page-game/"),
 ("AL", "KC"): dict(blue="KC", red="AL", first_pick="AL",
   bans={"AL": ["Jayce", "Rumble", "Syndra", "Ezreal", "Lulu"], "KC": ["Vi", "Qiyana", "Cassiopeia", "Seraphine", "Nautilus"]},
   picks=[P(1, "AL", "Nocturne", "Tarzan", "jungle"), P(2, "KC", "Jarvan IV", "Yike", "jungle"), P(3, "KC", "Orianna", "Kyeahoo", "mid"),
          P(4, "AL", "Olaf", "Breathe", "top"), P(5, "AL", "Akali", "Shanks", "mid"), P(6, "KC", "Jax", "Canna", "top"),
          P(7, "KC", "Renata Glasc", "Busio", "support"), P(8, "AL", "Miss Fortune", "Hope", "bot"), P(9, "AL", "Neeko", "Kael", "support"),
          P(10, "KC", "Kalista", "Caliste", "bot")], src="https://gol.gg/game/stats/83640/page-game/"),
 ("G2", "DK"): dict(blue="DK", red="G2", first_pick="DK",
   bans={"DK": ["Locke", "Nocturne", "Draven", "Kled", "Orianna"], "G2": ["Lucian", "Karma", "Caitlyn", "Lulu", "Seraphine"]},
   picks=[P(1, "DK", "Vi", "Lucid", "jungle"), P(2, "G2", "Kalista", "Hans Sama", "bot"), P(3, "G2", "Renata Glasc", "Labrov", "support"),
          P(4, "DK", "Syndra", "ShowMaker", "mid"), P(5, "DK", "Olaf", "Siwoo", "top"), P(6, "G2", "Jarvan IV", "SkewMond", "jungle"),
          P(7, "G2", "Viktor", "Caps", "mid"), P(8, "DK", "Ziggs", "Smash", "bot"), P(9, "DK", "Poppy", "Career", "support"),
          P(10, "G2", "K'Sante", "BrokenBlade", "top")], src="https://gol.gg/game/stats/83641/page-game/"),
 ("TLAW", "CFO"): dict(blue="TLAW", red="CFO", first_pick="TLAW",
   bans={"TLAW": ["Akali", "Vi", "Cassiopeia", "Ashe", "Draven"], "CFO": ["Orianna", "Ezreal", "Renata Glasc", "Nautilus", "Lulu"]},
   picks=[P(1, "TLAW", "Lee Sin", "Josedeodo", "jungle"), P(2, "CFO", "Rumble", "Rest", "top"), P(3, "CFO", "Qiyana", "Shad0w", "jungle"),
          P(4, "TLAW", "Galio", "Morgan", "top"), P(5, "TLAW", "Syndra", "Quid", "mid"), P(6, "CFO", "Viktor", "Pout", "mid"),
          P(7, "CFO", "Alistar", "Kino", "support"), P(8, "TLAW", "Jhin", "Yeon", "bot"), P(9, "TLAW", "Rakan", "CoreJJ", "support"),
          P(10, "CFO", "Aphelios", "Doggo", "bot")], src="https://gol.gg/game/stats/83639/page-game/"),
 ("LOS", "T1"): dict(blue="LOS", red="T1", first_pick="T1",
   bans={"T1": ["Nocturne", "Cassiopeia", "Poppy", "Kalista", "Nautilus"], "LOS": ["Bard", "Vi", "Qiyana", "Locke", "Akali"]},
   picks=[P(1, "T1", "Lee Sin", "Oner", "jungle"), P(2, "LOS", "Syndra", "Feisty", "mid"), P(3, "LOS", "Pantheon", "Curse", "jungle"),
          P(4, "T1", "Jhin", "Peyz", "bot"), P(5, "T1", "Jayce", "Doran", "top"), P(6, "LOS", "K'Sante", "Zest", "top"),
          P(7, "LOS", "Tristana", "Duduhh", "bot"), P(8, "T1", "Alistar", "Keria", "support"), P(9, "T1", "LeBlanc", "Faker", "mid"),
          P(10, "LOS", "Rakan", "Ackerman", "support")], src="https://gol.gg/game/stats/83643/page-game/"),
 ("TSW", "LYON"): dict(blue="LYON", red="TSW", first_pick="TSW",
   bans={"TSW": ["Syndra", "Renata Glasc", "Olaf", "Orianna", "Galio"], "LYON": ["Vi", "Qiyana", "Cassiopeia", "Jhin", "Corki"]},
   picks=[P(1, "TSW", "Ryze", "Dire", "mid"), P(2, "LYON", "Ezreal", "Berserker", "bot"), P(3, "LYON", "Nocturne", "Inspired", "jungle"),
          P(4, "TSW", "Lee Sin", "Hizto", "jungle"), P(5, "TSW", "Nautilus", "Bie", "support"), P(6, "LYON", "Alistar", "Isles", "support"),
          P(7, "LYON", "Anivia", "Saint", "mid"), P(8, "TSW", "Kai'Sa", "Eddie", "bot"), P(9, "TSW", "Rumble", "Pun", "top"),
          P(10, "LYON", "K'Sante", "Dhokla", "top")], src="https://gol.gg/game/stats/83644/page-game/"),
}

r1 = w["rounds"][0]
r1["status"] = "done"
r1["note"] = "先選權與藍紅方分開決定（高種子選先選權，另一隊選邊）"
for m in r1["matches"]:
    d = drafts[(m["a"], m["b"])]
    m.pop("picks", None)
    m.update(blue=d["blue"], red=d["red"], first_pick=d["first_pick"], draft_source=d["src"],
             draft={"order_known": True, "bans": d["bans"], "picks": d["picks"]})

# round 2 becomes an upcoming round; prices refreshed to 07:03 UTC (15:03 Taiwan)
pct_now = {("TES", "AL"): [36.5, 63.5], ("CFO", "MKOI"): [31.5, 68.5], ("G2", "LOS"): [81.5, 18.5], ("LYON", "KC"): [45.5, 54.5],
           ("TSW", "IG"): [29.5, 70.5], ("HLE", "GEN"): [42.5, 57.5], ("T1", "DK"): [56.5, 43.5], ("TLAW", "BLG"): [24.5, 75.5]}
if "next" in w:
    nxt = w.pop("next")
    for m in nxt["matches"]:
        m["pct"] = pct_now[(m["a"], m["b"])]
        m["poly"] = [round(100 / x, 2) for x in m["pct"]]
    w["rounds"].append({"name": nxt["name"], "status": "upcoming", "format": nxt["format"],
                        "date": "10/24 CDT · 10/25 01:00–08:00 台灣時間",
                        "note": "高分組先選權：CFO（抽籤）、LYON、GEN、T1；Polymarket 價格為 10/24 15:03 台灣時間",
                        "matches": nxt["matches"]})

# title odds from Polymarket price history: 1h before round 1 vs now
hist = {"GEN": (0.335, 0.345), "HLE": (0.175, 0.195), "T1": (0.155, 0.175), "DK": (0.0685, 0.106), "BLG": (0.165, 0.105),
        "AL": (0.053, 0.038), "G2": (0.0405, 0.0355), "IG": (0.0275, 0.0245), "KC": (0.0065, 0.013), "MKOI": (0.0035, 0.009),
        "LYON": (0.0035, 0.0045), "TLAW": (0.0095, 0.0025), "TES": (0.0085, 0.002), "CFO": (0.0005, 0.0015),
        "TSW": (0.0025, 0.0005), "LOS": (0.0005, 0.0005)}
o = w["outright"]
o["pre_label"] = "10/24 00:00 台灣時間，第一輪開打前 1 小時"
o["now_label"] = "10/24 15:02 台灣時間"
for r in o["rows"]:
    pre, now = hist[r["team"]]
    r["pre_poly"], r["poly"] = round(pre * 100, 2), round(now * 100, 2)
    r["pre_odds"], r["poly_odds"] = round(1 / pre, 2), round(1 / now, 2)
o["rows"].sort(key=lambda r: -r["poly"])

# advance: market (Polymarket) + model (Outdrafted) record distribution
model = {"GEN": (46, 33, 15, 94), "T1": (39, 31, 18, 89), "HLE": (32, 36, 21, 89), "DK": (28, 32, 23, 83), "BLG": (0, 30, 35, 65),
         "MKOI": (23, 22, 19, 63), "KC": (20, 22, 20, 62), "G2": (0, 25, 30, 55), "AL": (0, 19, 30, 50), "IG": (0, 20, 27, 47),
         "TES": (0, 7.1, 17, 24), "LYON": (7, 7.9, 8.9, 24), "CFO": (4.6, 5.8, 7.1, 17), "TLAW": (0, 3.5, 11, 15),
         "LOS": (0, 2.8, 9.2, 12), "TSW": (0, 2.9, 7.2, 10)}
market = {"GEN": (94, 44, None), "T1": (89, 39.5, None), "HLE": (90.5, 28.5, None), "DK": (75.5, 24.5, None), "KC": (51, 21.95, None),
          "MKOI": (64.5, 19.6, None), "LYON": (51, 13.9, None), "CFO": (22.5, 12.1, None), "LOS": (10.3, None, 79),
          "TLAW": (15.5, None, 52.5), "TSW": (11.5, None, 41.5), "TES": (22, None, 34), "IG": (43.5, None, 14.55),
          "AL": (48, None, 8.5), "G2": (55, None, 6.65), "BLG": (61, None, 6.15)}
w["advance"] = {
 "cols": [
  {"key": "ko", "label": "晉級 %（市場）", "note": "Polymarket 晉級淘汰賽市場，成交量小、價差大"},
  {"key": "x30", "label": "3-0 %（市場）", "note": "Polymarket"},
  {"key": "m30", "label": "3-0 %（模型）", "note": "Outdrafted 模型"},
  {"key": "m31", "label": "3-1 %（模型）", "note": "Outdrafted 模型，Polymarket 沒有 3-1 市場"},
  {"key": "m32", "label": "3-2 %（模型）", "note": "Outdrafted 模型，Polymarket 沒有 3-2 市場"},
  {"key": "madv", "label": "晉級 %（模型）", "note": "Outdrafted 模型 = 3-0 + 3-1 + 3-2"},
  {"key": "x03", "label": "0-3 %（市場）", "note": "Polymarket"}],
 "rows": sorted(({"team": t, "ko": market[t][0], "x30": market[t][1], "x03": market[t][2],
                  "m30": model[t][0], "m31": model[t][1], "m32": model[t][2], "madv": model[t][3]} for t in model),
                key=lambda r: -r["ko"])}

w["collected"] = "2026-10-24 15:03（台灣時間）"
w["notes"] = [
 "賽果、時長與擊殺數取自 Liquipedia；完整 BP（禁用、選用順序、路線）取自 gol.gg 各場頁面，並與 Liquipedia 核對。擊殺數為各選手 KDA 加總。",
 "2026 世界賽的先選權與藍紅方分開決定：8 場中有 6 場是紅方先選。選用下方數字為全場第幾手（先選方為第 1、4、5、8、9 手）。禁用只知道各隊自己的順序（前 3 + 後 2），兩隊交錯順序沒有來源。",
 "冠軍機率與賠率取自 Polymarket 價格歷史：第一輪前 = 10/24 00:00（台灣時間，開打前 1 小時），現在 = 10/24 15:02。G2 在 00:00 的價格（4.05%）看起來是短暫跳動，前後一小時約 3.5%。Kalshi 冷門隊以 1 美分為下限，賠率超過約 66 時沒有參考價值。",
 "3-1、3-2 只有 Outdrafted 模型數字，Polymarket 沒有這類市場；淘汰方的 1-3、2-3 分布沒有來源。「晉級（市場）」成交量小、價差大，請保守看待。賠率會變動，下注前請以莊家即時盤口為準。",
 "第一輪之後的傳統莊家賠率（bet365、Pinnacle 等）未取得；「賽前 Stake」欄為 10/12 的冠軍賠率（經 win.gg）。"]
if not any("gol.gg" in s[1] for s in w["sources"]):
    w["sources"] += [["gol.gg：Worlds 2026 各場 BP", "https://gol.gg/game/stats/83638/page-game/"],
                     ["Polymarket 價格歷史（CLOB）", "https://clob.polymarket.com/prices-history"]]
json.dump(w, open(path, "w"), ensure_ascii=False, indent=1)
print("rounds:", [(r["name"], r["status"], len(r["matches"])) for r in w["rounds"]])
