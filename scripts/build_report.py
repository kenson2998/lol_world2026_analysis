"""Turn soloq_raw.json into CSV / Markdown / a single-page HTML report.

usage: python3 -I build_report.py out_dir rosters.json
"""
import base64, csv, json, os, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from soloq import N_GAMES, summarize

ROLE_ZH = {"top": "上路", "jungle": "打野", "mid": "中路", "bot": "下路", "support": "輔助"}
POS_ROLE = {"TOP": "top", "JUNGLE": "jungle", "MID": "mid", "ADC": "bot", "SUPPORT": "support"}
WINDOW_START = "2026-10-11"  # window end is the day the data was pulled
FOOTER = (
    "<p>統計期間：2026-10-11 至資料擷取日（韓國時間），期間外的場次不計；選手不在本職位置的補位場次也不計。"
    "黃色底色代表與上一次更新相比有變動的數字（滑鼠移上可看上一次的數值）。"
    "「最後上線」為該選手在韓服／美服各自最近一場單排，距資料擷取時間多久，不受期間與位置篩選影響。"
    "英雄圖示取自 Riot Data Dragon，選手頭像取自 LoL Esports 官方資料。</p>"
    "<p>資料來源：先發名單取自 GosuGamers〈All teams and players qualified for Worlds 2026〉；TES 上路因 ZUIAN 簽證問題以 369 列計。"
    "選手帳號取自 TrackingThePros（選手頁與 Worlds 美服 Bootcamp 追蹤）、AussyELO Worlds Pro Tracker 與 OP.GG 職業選手資料庫，"
    "戰績取自 OP.GG（公開 MCP API），只計單雙排（SOLORANKED），重開局不計。"
    "T1、GEN、HLE 的美服帳號由使用者提供（10/19 起開始在美服單排，與 TrackingThePros 一致）；"
    "DK 全隊與 AL Shanks 的美服帳號取自 TrackingThePros Bootcamp（10/21 更新）；"
    "部分 LPL、TSW、LOS 選手的美服帳號取自 OP.GG 職業選手資料庫。dpm.lol 有 Cloudflare 驗證，無法自動讀取。</p>"
    "<p>限制：只抓韓服與美服帳號，主要在其他伺服器（EUW、BR、TW/VN、國服）練習的選手樣本會少或為零；"
    "每個帳號最多讀最近 20 場（含非單排），合併後取最新 20 場單排，因此部分選手不足 20 場。"
    "標示「帳號歸屬待確認」者，帳號來源網站登記的隊伍與本名單不同，可能是資料過期或同名選手。</p>")


def role_meta(players):
    """Champion totals per role across all players, counting only games played in that role."""
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0, set()]))
    for p in players:
        for g in p["games"]:
            if POS_ROLE.get(g["position"]) != p["role"]:
                continue
            a = agg[p["role"]][g["champion"]]
            a[0] += 1
            a[1] += g["result"] == "WIN"
            a[2].add(p["player"])
    out = {}
    for role, champs in agg.items():
        rows = [{"champion": c, "games": k, "wins": w, "win_rate": round(w / k * 100, 1), "players": len(ps)}
                for c, (k, w, ps) in champs.items()]
        rows.sort(key=lambda r: (-r["games"], -r["win_rate"]))
        out[role] = rows[:12]
    return out


acct_id = lambda a: f'{a["region"]}:{a["game_name"]}#{a["tagline"]}'


def short_when(prev):
    """'2026-10-21 12:37 KST' -> '10/21 12:37'."""
    f = prev["fetched"]
    return f"{f[5:7]}/{f[8:10]} {f[11:16]}"


def load_prev(out_dir):
    path = f"{out_dir}/report_state_prev.json"
    return json.load(open(path)) if os.path.exists(path) else None


def gw(r):
    """Games / wins / win rate, e.g. '4場 2勝 50%'."""
    return f'{r["games"]}場 {r["wins"]}勝 {round(r["win_rate"])}%'


def rec_txt(s):
    return gw(s) if s and s["games"] else "沒有本位單排資料"


def player_diff(p, old, when):
    """What changed for one player since the previous build, with plain-language tooltips naming the previous build."""
    s = p["summary"]
    new_champ = f"新英雄：上次（{when}）還沒用過"
    if not old:
        return {"record": bool(s["games"]), "prev_record": rec_txt(None), "prev_games": 0, "prev_wins": 0,
                "champs": {c["champion"]: new_champ for c in s["champions"]},
                "last": {r: True for r in p["last_played"]}, "new_accounts": [acct_id(a) for a in p["accounts"]]}
    os_ = old["summary"]
    old_champs = {c["champion"]: c for c in os_["champions"]}
    champs = {}
    for c in s["champions"]:
        o = old_champs.get(c["champion"])
        if not o:
            champs[c["champion"]] = new_champ
        elif (o["games"], o["wins"]) != (c["games"], c["wins"]):
            champs[c["champion"]] = f'上次（{when}）{gw(o)} → 現在 {gw(c)}'
    return {"record": (os_["games"], os_["wins"]) != (s["games"], s["wins"]), "prev_record": rec_txt(os_),
            "prev_games": os_["games"], "prev_wins": os_["wins"],
            "champs": champs,
            "last": {r: t != old["last_played"].get(r) for r, t in p["last_played"].items()},
            "new_accounts": [acct_id(a) for a in p["accounts"] if acct_id(a) not in old["accounts"]]}


def meta_diff(meta, old_meta, when):
    """Per role, champions whose role-wide totals moved, with the previous totals."""
    out = {}
    for role, rows in meta.items():
        old = {r["champion"]: r for r in old_meta.get(role, [])}
        out[role] = {r["champion"]: (f'上次（{when}）{gw(old[r["champion"]])} → 現在 {gw(r)}'
                                     if r["champion"] in old else f"新進榜：上次（{when}）不在前 {len(rows)} 名")
                     for r in rows if r["champion"] not in old
                     or (old[r["champion"]]["games"], old[r["champion"]]["wins"]) != (r["games"], r["wins"])}
    return out


def ago(t, now):
    """Elapsed time from an OP.GG timestamp to `now`, as 'X天X小時X分前' ('—' when there is none)."""
    if not t:
        return "—"
    mins = max(0, int((now - datetime.fromisoformat(t)).total_seconds() // 60))
    d, h, m = mins // 1440, mins % 1440 // 60, mins % 60
    return (f"{d}天" if d else "") + (f"{h}小時" if d or h else "") + f"{m}分前"


def load_zh(out_dir):
    """English champion name -> Taiwan-server (zh_TW) name, from champ_icons.json."""
    path = f"{out_dir}/champ_icons.json"
    return json.load(open(path)).get("zh_TW", {}) if os.path.exists(path) else {}


ZH = {}


def cname(c):
    """'Ahri' -> 'Ahri (阿璃)'."""
    return f"{c} ({ZH[c]})" if c in ZH else c


def used_champs(players, worlds):
    return {g["champion"] for p in players for g in p["games"]} | worlds_picks(worlds)


def worlds_picks(worlds):
    """Champion names picked or banned in Worlds games, so their icons get inlined too (Teemo: a 水晶球 question)."""
    names = {"Teemo"} if worlds else set()
    for r in (worlds or {}).get("rounds", []):
        for g in (g for m in r["matches"] for g in m.get("games") or [m]):
            d = g.get("draft") or {}
            names |= {p["champion"] for p in d.get("picks", [])}
            names |= {c for bans in (d.get("bans") or {}).values() for c in bans}
    return names


def used_icons(out_dir, players, extra=()):
    """Only inline icons for champions that appear, to keep the page small."""
    path = f"{out_dir}/champ_icons.json"
    if not os.path.exists(path):
        return {}
    icons = json.load(open(path))["icons"]
    used = {g["champion"] for p in players for g in p["games"]} | set(extra)
    missing = sorted(used - icons.keys())
    if missing:
        print(f"no icon for: {missing}", file=sys.stderr)
    return {c: icons[c] for c in used if c in icons}


def main(out_dir, roster_path):
    players = json.load(open(f"{out_dir}/soloq_raw.json"))
    ZH.update(load_zh(out_dir))
    # "last online" is measured against when the data was pulled, not when the page is opened
    fetched = datetime.fromtimestamp(os.path.getmtime(f"{out_dir}/soloq_raw.json"), timezone(timedelta(hours=9)))
    window = (WINDOW_START, fetched.strftime("%Y-%m-%d"))
    role_pos = {v: k for k, v in POS_ROLE.items()}
    for p in players:
        # latest solo game per server, before the window / role filters
        p["last_played"] = {}
        for g in p["games"]:
            region = g["account"].split(":")[0]
            if g["time"] > p["last_played"].get(region, ""):
                p["last_played"][region] = g["time"]
        # created_at is KST; compare the local date part
        p["games"] = [g for g in p["games"] if window[0] <= g["time"][:10] <= window[1]]
        # positions before dropping fill games, so a mostly-off-role account still gets flagged
        p["positions_all"] = summarize(p["games"])["positions"]
        # fill games go first, then the cap, so each player keeps up to N_GAMES games in their own role
        p["games"] = sorted((g for g in p["games"] if g["position"] == role_pos[p["role"]]),
                            key=lambda g: g["time"], reverse=True)[:N_GAMES]
        p["summary"] = summarize(p["games"])
    rosters = {t["team"]: t for t in json.load(open(roster_path))}

    with open(f"{out_dir}/soloq_champions.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["team", "role", "player", "solo_games", "player_wr", "champion", "champion_zh_tw", "games", "wins",
                    "pick_rate_%", "win_rate_%", "last_online_kr", "last_online_na", "accounts"])
        for p in players:
            s, lp = p["summary"], p["last_played"]
            accts = "; ".join(f'{a["region"]}:{a["game_name"]}#{a["tagline"]}' for a in p["accounts"])
            for c in s["champions"] or [{}]:
                w.writerow([p["team"], p["role"], p["player"], s["games"], s["win_rate"], c.get("champion"), ZH.get(c.get("champion"), ""),
                            c.get("games"), c.get("wins"), c.get("pick_rate"), c.get("win_rate"),
                            ago(lp.get("KR"), fetched), ago(lp.get("NA"), fetched), accts])

    md = [f"# Worlds 2026 十六強 單排英雄使用率／勝率（{window[0][5:].replace('-', '/')}–{window[1][5:].replace('-', '/')}）", ""]
    for team in rosters:
        md += [f"## {team}", "", "| 位置 | 選手 | 場數 | 戰績 | 勝率 | 最後上線 | 常用英雄（場數・使用率・勝率）|",
               "|---|---|---|---|---|---|---|"]
        for p in (x for x in players if x["team"] == team):
            s = p["summary"]
            champs = "、".join(f'{cname(c["champion"])} {c["games"]}場 {c["pick_rate"]:.0f}% {c["win_rate"]:.0f}%'
                              for c in s["champions"][:6]) or "—"
            rec = f'{s["wins"]}-{s["games"] - s["wins"]}' if s["games"] else "—"
            wr = f'{s["win_rate"]:.0f}%' if s["games"] else "—"
            last = "<br>".join(f'[{r}] {ago(p["last_played"].get(r), fetched)}' for r in ("KR", "NA"))
            md.append(f'| {ROLE_ZH[p["role"]]} | {p["player"]} | {s["games"]} | {rec} | {wr} | {last} | {champs} |')
        md.append("")
    if os.path.exists(f"{out_dir}/worlds.json"):
        w = json.load(open(f"{out_dir}/worlds.json"))
        md += [f"## 世界賽戰況（整理於 {w['collected']}）", "", w["status"], ""]
        for r in w["rounds"]:
            done = [m for m in r["matches"] if m.get("winner")]
            todo = [m for m in r["matches"] if not m.get("winner")]
            if done:
                md += [f"### {r['name']}結果（{r['format']}）", "", "| 對戰 | 勝方 | 擊殺 | 時長 | 選用（BP 順序） | 備註 |", "|---|---|---|---|---|---|"]
                for m in done:
                    games = m.get("games") or [m]
                    md += [f"| {m['a']} vs {m['b']}{f' 第{i + 1}局' if len(games) > 1 else ''} | {g['winner']} | {'-'.join(map(str, g.get('kills') or []))} | "
                           f"{g.get('length', '')} | "
                           + "、".join(f"{p['team']} {cname(p['champion'])}" for p in sorted((g.get('draft') or {}).get('picks', []), key=lambda p: p['n']))
                           + f" | {m.get('note', '')} |" for i, g in enumerate(games)]
                md.append("")
            if todo:
                md += [f"### {r['name']}（{r['format']}，未開打）", "", "| 台灣時間 | 組別 | 對戰 | Polymarket 勝率 | 賠率 Polymarket | 賠率 Kalshi |",
                       "|---|---|---|---|---|---|"]
                md += [f"| {m['time_tw']} | {m['pool']} | {m['a']} vs {m['b']} | {' / '.join(f'{x}%' for x in m.get('pct') or []) or '—'} | "
                       f"{' / '.join(map(str, m.get('poly') or ['—']))} | {' / '.join(map(str, m.get('kalshi') or ['—']))} |" for m in todo]
                md.append("")
        o = w["outright"]
        md += ["", f"### 冠軍機率（{o['now_label']}，對比 {o['pre_label']}）", "",
               "| 隊伍 | Polymarket % | 第一輪前 % | Kalshi % | 十進位賠率 | 賽前 Stake |", "|---|---|---|---|---|---|"]
        md += [f"| {r['team']} | {r['poly']} | {r['pre_poly']} | {r['kalshi']} | {r['poly_odds']} | {r.get('pre_stake', '—')} |" for r in o["rows"]]
        md += [""] + [f"- {n}" for n in w["notes"]] + ["", "來源：" + "、".join(f"[{n}]({u})" for n, u in w["sources"]), ""]
    open(f"{out_dir}/soloq_report.md", "w").write("\n".join(md))

    prev = load_prev(out_dir)
    meta = role_meta(players)
    worlds = json.load(open(f"{out_dir}/worlds.json")) if os.path.exists(f"{out_dir}/worlds.json") else None
    for p in players:
        p["changed"] = player_diff(p, prev.get("players", {}).get(f'{p["team"]}/{p["role"]}'), short_when(prev)) if prev else {}
    data = {"teams": [{"team": t, "region": r.get("region", ""), "full": r.get("full", t),
                       "players": [{k: p[k] for k in ("role", "player", "accounts", "summary", "ttp_team", "team_mismatch",
                                                      "last_played", "changed")}
                                   | {"positions": p["positions_all"]}
                                   for p in players if p["team"] == t]} for t, r in rosters.items()],
            "meta": meta,
            "meta_changed": meta_diff(meta, prev["meta"], short_when(prev)) if prev else {},
            "prev_fetched": prev["fetched"] if prev else None,
            "window": list(window),
            "worlds": worlds,
            "icons": used_icons(out_dir, players, worlds_picks(worlds)),
            "zh": {c: ZH[c] for c in used_champs(players, worlds) if c in ZH},
            "avatars": json.load(open(f"{out_dir}/player_avatars.json")) if os.path.exists(f"{out_dir}/player_avatars.json") else {},
            "fetched": fetched.strftime("%Y-%m-%d %H:%M KST"),
            "fetched_iso": fetched.isoformat(),
            "footer": FOOTER}
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_template.html")).read()
    page = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
    # favicon is inlined so the standalone page carries it too
    icon = f"{out_dir}/favicon.png"
    page = page.replace("/*FAVICON*/", "data:image/png;base64," + base64.b64encode(open(icon, "rb").read()).decode() if os.path.exists(icon) else "")
    # this build becomes the baseline the next update is compared against (copy it to report_state_prev.json first)
    json.dump({"fetched": data["fetched"], "meta": meta,
               "players": {f'{p["team"]}/{p["role"]}': {"summary": p["summary"], "last_played": p["last_played"],
                                                         "accounts": [acct_id(a) for a in p["accounts"]]} for p in players}},
              open(f"{out_dir}/report_state.json", "w"), ensure_ascii=False)
    open(f"{out_dir}/worlds2026_soloq.html", "w").write(page)

    # Standalone copy that opens straight from disk: the artifact host normally supplies this skeleton
    cut = page.index("</style>") + len("</style>")
    standalone = ('<!doctype html>\n<html lang="zh-Hant">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<style>:root{color-scheme:light}body{margin:0;font:14px/1.5 system-ui,sans-serif}"
        "img{max-width:100%}[hidden]{display:none!important}</style>\n"
        + page[:cut] + "\n</head>\n<body>\n" + page[cut:] + "\n</body>\n</html>\n")
    open(f"{out_dir}/worlds2026_analysis.html", "w").write(standalone)
    # a dated snapshot (Taiwan date) goes to EXPORT_DIR when set, so the repo keeps one undated page
    if os.environ.get("EXPORT_DIR"):
        dated = os.path.join(os.environ["EXPORT_DIR"], f"worlds2026_{datetime.now(timezone(timedelta(hours=8))).strftime('%m%d')}.html")
        open(dated, "w").write(standalone)
        print(f"wrote {dated}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
