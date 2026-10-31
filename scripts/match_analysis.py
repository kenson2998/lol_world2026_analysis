"""Pre-match draft analysis for every unplayed match of the current round, in the match_analysis_format.md style.

For each match it writes
  data/analysis/<id>_<A>_vs_<B>.html   a standalone page (linked from the match preview on the site)
  <export>/<id>_<A>_vs_<B>.txt         the plain-text version
  <export>/<id>_<A>_vs_<B>.png         an image of the page (needs python3.11 + playwright)
where <id> is the site's share id, e.g. r4-m3 = round 4, 3rd match.

usage: python3 -I match_analysis.py data_dir [export_dir]
"""
import base64, html, json, os, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

data_dir = sys.argv[1]
export = sys.argv[2] if len(sys.argv) > 2 else None
W = json.load(open(f"{data_dir}/worlds.json"))
CH = json.load(open(f"{data_dir}/champ_icons.json"))
ZH, ICONS = CH.get("zh_TW", {}), CH["icons"]
ROLES = {"top": "上路", "jungle": "打野", "mid": "中路", "bot": "下路", "support": "輔助"}
NUM = "一二三四五六七八九十"
zh = lambda c: ZH.get(c, c)
# site icon (inlined) and today's Taiwan date, which names the dated snapshot the exported copies link home to
FAVICON = ("data:image/png;base64," + base64.b64encode(open(f"{data_dir}/favicon.png", "rb").read()).decode()
           if os.path.exists(f"{data_dir}/favicon.png") else "")
TODAY = datetime.now(timezone(timedelta(hours=8))).strftime("%m%d")

# every finished game with a draft, tagged with its two teams
games = [(m["a"], m["b"], g) for r in W["rounds"] for m in r["matches"] if m.get("winner")
         for g in (m.get("games") or [m]) if g.get("draft")]


def team_draft(team):
    """picks (n, wins), opponent picks against it (n, its wins), its bans, bans against it — per champion."""
    s = {k: defaultdict(lambda: [0, 0]) for k in ("pick", "face", "ban", "banned")}
    n = 0
    for a, b, g in games:
        if team not in (a, b):
            continue
        n += 1
        opp, win = (b if team == a else a), g["winner"] == team
        for p in g["draft"]["picks"]:
            x = s["pick" if p["team"] == team else "face"][p["champion"]]
            x[0] += 1; x[1] += win
        for c in g["draft"]["bans"].get(team, []):
            s["ban"][c][0] += 1
        for c in g["draft"]["bans"].get(opp, []):
            s["banned"][c][0] += 1
    return n, s


def top_groups(counts, k=3):
    """Champions grouped by count, highest first, until k champions are covered; a tail of 1s is dropped once
    something ranks above it. Returns ([(count, [champs])], dropped_ones)."""
    by = defaultdict(list)
    for c, (n, _) in counts.items():
        by[n].append(c)
    out, seen = [], 0
    for n in sorted(by, reverse=True):
        if seen >= k:
            break
        if n == 1 and out:
            return out, True
        out.append((n, sorted(by[n], key=zh)))
        seen += len(by[n])
    return out, False


def groups_text(groups, dropped, verb):
    parts = []
    for i, (n, cs) in enumerate(groups):
        names = ", ".join(zh(c) for c in cs)
        if len(cs) == 1:
            parts.append(names)
        else:
            t = f"{names} 共列第{NUM[i]}"
            parts.append(t if i == 0 else f"({t})")
    s = ", ".join(parts) or "無"
    return s + (f"... etc 都只{verb}1次後不列出" if dropped else "")


def champ_lines(c, A, B):
    """One line per team describing what it did with/against champion c."""
    def facts(s):
        return s["pick"].get(c, [0, 0]), s["face"].get(c, [0, 0]), s["ban"].get(c, [0, 0])[0], s["banned"].get(c, [0, 0])[0]

    def line(s):
        (pn, pw), (fn, fw), bn, xn = facts(s)
        if not (pn or fn or bn or xn):
            return "沒數據"
        out = []
        if pn == 1:
            out.append(f"選1次{'贏' if pw else '輸'}")
        elif pn:
            out.append(f"選{pn}次都贏, 100%勝率" if pw == pn else f"選{pn}次都輸, 0%勝率" if pw == 0
                       else f"選{pn}次 {pw}勝{pn - pw}敗（{round(pw / pn * 100)}%勝率）")
        if fn == 1:
            out.append(f"對面選1次, 應對{'贏了' if fw else '輸了'}")
        elif fn:
            out.append(f"應對{fn}場都贏, 100%勝率" if fw == fn else f"對面選的話, 應對勝率0%（{fn}場）" if fw == 0
                       else f"應對{fn}場 {fw}勝{fn - fw}敗（{round(fw / fn * 100)}%勝率）")
        if bn and xn and not pn and not fn:
            out.append(f"非ban即被ban（自ban{bn}次、被ban{xn}次）")
        else:
            if bn:
                out.append(f"自ban{bn}次")
            if xn:
                out.append(f"被ban{xn}次")
            if not pn and not fn:
                out.append("沒選和對戰數據")
        return ", ".join(out)

    fa, fb = facts(A[1]), facts(B[1])
    lead = []
    if not any(f[0][0] or f[1][0] for f in (fa, fb)) and any(f[2] or f[3] for f in (fa, fb)):
        lead.append("目前兩隊都沒選過也沒對上, 都在ban位")
    if fa[1][0] and fb[1][0] and fa[1][1] == fa[1][0] and fb[1][1] == fb[1][0] and not fa[0][0] and not fb[0][0]:
        lead.append("雙方應對都100%勝率")
    return lead, line(A[1]), line(B[1])


def analyse(a, b):
    A, B = team_draft(a), team_draft(b)
    # tournament-wide: champions with the best pick win rate (at least 3 picks)
    allp = defaultdict(lambda: [0, 0])
    for _, _, g in games:
        for p in g["draft"]["picks"]:
            x = allp[p["champion"]]; x[0] += 1; x[1] += g["winner"] == p["team"]
    best = sorted(((c, n, w) for c, (n, w) in allp.items() if n >= 3), key=lambda t: (-t[2] / t[1], -t[1], zh(t[0])))[:3]
    lists = {}
    for team, (n, s) in ((a, A), (b, B)):
        lists[team] = {"banned": top_groups(s["banned"]), "ban": top_groups(s["ban"])}
    # champions worth a look: the ban lists, anything either team picked 2+ times, anything both teams faced
    pick_list = lambda s: {c for c, (n, _) in s["pick"].items() if n >= 2}
    noted = set()
    for team in (a, b):
        for key in ("banned", "ban"):
            for _, cs in lists[team][key][0]:
                noted |= set(cs)
    noted |= pick_list(A[1]) | pick_list(B[1]) | (set(A[1]["face"]) & set(B[1]["face"]))
    involve = lambda c: sum(s[k].get(c, [0])[0] for s in (A[1], B[1]) for k in ("pick", "face", "ban", "banned"))
    noted = sorted(noted, key=lambda c: (-involve(c), zh(c)))[:10]
    return A, B, best, lists, [(c, *champ_lines(c, A, B)) for c in noted]


def record(team):
    """Swiss record, series W-L and game W-L of a team over finished matches."""
    rec = next((k for k, ts in W["standings"].items() if team in ts), "")
    ms = [m for r in W["rounds"] for m in r["matches"] if m.get("winner") and team in (m["a"], m["b"])]
    gs = [g for m in ms for g in (m.get("games") or [m])]
    return rec, sum(m["winner"] == team for m in ms), len(ms), sum(g.get("winner") == team for g in gs), len(gs)


def lane_rows(team):
    """Per lane, the team's player with the most games there and their averages from W["player_games"]."""
    by = defaultdict(list)
    for g in W.get("player_games", []):
        if g["team"] == team:
            by[(g["role"], g["player"])].append(g)
    avg = lambda gs, f: (lambda v: sum(v) / len(v) if v else None)([x[f] for x in gs if x.get(f) is not None])
    out = {}
    for (role, player), gs in by.items():
        if role in out and len(out[role]["gs"]) >= len(gs):
            continue
        k, d, a_ = (sum(x.get(f) or 0 for x in gs) for f in ("k", "d", "a"))
        out[role] = {"player": player, "gs": gs, "kda": (k + a_) / max(1, d), "gd15": avg(gs, "gd15"), "dpm": avg(gs, "dpm"), "kp": avg(gs, "kp")}
    return out


def team_game_stats(team):
    """Per finished game of the team: its kills, kills against it, and length in minutes."""
    out = []
    for r in W["rounds"]:
        for m in r["matches"]:
            if not m.get("winner") or team not in (m["a"], m["b"]):
                continue
            i = 0 if team == m["a"] else 1
            for g in m.get("games") or [m]:
                if g.get("kills") and g.get("length"):
                    mm, ss = map(int, g["length"].split(":"))
                    out.append((g["kills"][i], g["kills"][1 - i], mm + ss / 60))
    return out


def summary(a, b, A, B, mid):
    """賽事總結: only facts from the finished games — records, draft overlaps, lane numbers, team averages."""
    S = []
    # records, head-to-head, pre-match price if any
    lines = []
    for t in (a, b):
        rec, sw, sn, gw, gn = record(t)
        lines.append(f"{t}：瑞士輪 {rec}，系列賽 {sw}勝{sn - sw}敗，單局 {gw}勝{gn - gw}敗")
    h2h = [m for r in W["rounds"] for m in r["matches"] if m.get("winner") and {m["a"], m["b"]} == {a, b}]
    lines.append("本屆交手：" + ("、".join(f"{m['winner']} 勝" + (f"（{max(m['score'])}-{min(m['score'])}）" if m.get("score") else "") for m in h2h) if h2h else "尚未交手"))
    ri, k = int(mid[1:mid.index("-")]) - 1, int(mid[mid.index("m") + 1:]) - 1
    m = W["rounds"][ri]["matches"][k]
    pct = m.get("pct") or (lambda bs: bs and (lambda pa: [round(pa * 100, 1), round(100 - pa * 100, 1)])(
        sum((1 / x["odds"][0]) / (1 / x["odds"][0] + 1 / x["odds"][1]) for x in bs) / len(bs)))(m.get("books"))
    lines.append(f"賽前勝率：{a} {pct[0]}% / {b} {pct[1]}%" + ("" if m.get("pct") else "（莊家賠率換算）") if pct else "賽前勝率：尚未取得 Polymarket 價格或莊家賠率")
    S.append(("戰績與交手", lines))

    # draft: what one side bans that the other picks, what both only ban, each side's best picks
    lines = []
    sa, sb = A[1], B[1]
    for (t, s), (u, o) in (((a, sa), (b, sb)), ((b, sb), (a, sa))):
        for c, (bn, _) in sorted(s["ban"].items(), key=lambda kv: (-kv[1][0], zh(kv[0]))):
            pn, pw = o["pick"].get(c, [0, 0])
            if bn >= 2 and pn >= 2:
                lines.append(f"{t} 禁過 {zh(c)} {bn} 次，{u} 選過 {pn} 次（{pw}勝{pn - pw}敗）")
    both = [c for c in set(sa["ban"]) | set(sa["banned"]) if c in set(sb["ban"]) | set(sb["banned"])
            and not any(s[k].get(c, [0])[0] for s in (sa, sb) for k in ("pick", "face"))]
    both = sorted(both, key=lambda c: (-sum(s[k].get(c, [0])[0] for s in (sa, sb) for k in ("ban", "banned")), zh(c)))[:4]
    if both:
        lines.append("兩隊都只禁不選（雙方對局皆未出場）：" + "、".join(
            f"{zh(c)}（{a} 禁{sa['ban'].get(c, [0])[0]}被禁{sa['banned'].get(c, [0])[0]}、{b} 禁{sb['ban'].get(c, [0])[0]}被禁{sb['banned'].get(c, [0])[0]}）" for c in both))
    for t, s in ((a, sa), (b, sb)):
        top = sorted(((c, n, w) for c, (n, w) in s["pick"].items() if n >= 2), key=lambda x: (-x[2] / x[1], -x[1], zh(x[0])))[:3]
        lines.append(f"{t} 選用 2 次以上的英雄（依勝率排序，前三）：" + ("、".join(f"{zh(c)} {round(w / n * 100)}%（{w}勝{n - w}敗）" for c, n, w in top) or "無（沒有選用 2 次以上的英雄）"))
    S.append(("BP 重點", lines))

    # lanes: the usual player of each side, their averages, and who leads each number
    La, Lb = lane_rows(a), lane_rows(b)
    f1 = lambda v: "—" if v is None else f"{v:.1f}"
    f0 = lambda v: "—" if v is None else f"{round(v):,}"
    sg = lambda v: "—" if v is None else f"{'+' if v > 0 else ''}{round(v):,}"
    lines, lead = [], {"kda": [0, 0], "gd15": [0, 0], "dpm": [0, 0]}
    for role, name in ROLES.items():
        x, y = La.get(role), Lb.get(role)
        if not x or not y:
            continue
        for key in lead:
            if x[key] is not None and y[key] is not None and x[key] != y[key]:
                lead[key][0 if x[key] > y[key] else 1] += 1
        lines.append(f"{name} {x['player']} vs {y['player']}：KDA {f1(x['kda'])} / {f1(y['kda'])}、15分經濟差 {sg(x['gd15'])} / {sg(y['gd15'])}、"
                     f"每分傷害 {f0(x['dpm'])} / {f0(y['dpm'])}、參團率 {f0(x['kp'])}% / {f0(y['kp'])}%")
    lines.append("領先路線數（{a} : {b}）：KDA {k[0]}:{k[1]}、15分經濟差 {g[0]}:{g[1]}、每分傷害 {d[0]}:{d[1]}".format(
        a=a, b=b, k=lead["kda"], g=lead["gd15"], d=lead["dpm"]))
    S.append(("各路線對位數據（本屆平均）", lines))

    # team averages per game
    lines = []
    for t in (a, b):
        gs = team_game_stats(t)
        if gs:
            n, sec = len(gs), round(sum(x[2] for x in gs) / len(gs) * 60)
            lines.append(f"{t}：每局平均擊殺 {sum(x[0] for x in gs) / n:.1f}、陣亡 {sum(x[1] for x in gs) / n:.1f}、時長 {sec // 60}:{sec % 60:02d}（{n} 局）")
    S.append(("隊伍每局數據", lines))
    return S


def as_text(a, b, mid, A, B, best, lists, champs, summ):
    L = [f"{a} vs {b} 觀賽前的選角數據分析：", "", "賽事總結:"]
    for title, lines in summ:
        L += [f"【{title}】"] + [f"- {x}" for x in lines]
    L += ["", "值得注意的選角:", "當前賽事勝率最高前三（至少選用 3 次）"]
    L += [f"{i + 1}. {zh(c)}（{c}）{round(w / n * 100)}%（{w}勝{n - w}敗）" for i, (c, n, w) in enumerate(best)]
    for key, title, verb in (("banned", "被ban前三", "被ban"), ("ban", "ban前三", "ban")):
        L += ["", f"{title}:"] + [f"{t}：{groups_text(*lists[t][key], verb)}" for t in (a, b)]
    for c, lead, la, lb in champs:
        L += ["", f"{zh(c)}:"] + lead + [f"{a}: {la}", f"{b}: {lb}"]
    L += ["", f"（{a} {A[0]} 局、{b} {B[0]} 局的 BP 統計，勝率皆為該隊在那些局的戰績；資料整理於 {W['collected']}）"]
    return "\n".join(L) + "\n"


def as_html(a, b, mid, rname, A, B, best, lists, champs, summ, home):
    """home: link back to the site's main page, relative to this page's folder."""
    e = html.escape
    icon = lambda c: (f'<img src="{ICONS[c]}" alt="" width="28" height="28">' if c in ICONS else "") + f"<span>{e(zh(c))}</span>"
    chip = lambda c, n=None: f'<span class="ch" title="{e(c)}">{icon(c)}{f"<b>×{n}</b>" if n else ""}</span>'
    def groups(t, key, verb):
        gs, dropped = lists[t][key]
        out = "".join(f'<span class="grp">{"".join(chip(c, n) for c in cs)}{f"<i>共列第{NUM[i]}</i>" if len(cs) > 1 else ""}</span>' for i, (n, cs) in enumerate(gs)) or "無"
        return out + (f'<span class="more">其餘都只{verb}1次，不列出</span>' if dropped else "")
    rows = "".join(f"""<section class="champ"><h3>{chip(c)}</h3>{"".join(f'<p class="lead">{e(x)}</p>' for x in lead)}
      <p><b class="ta">{e(a)}</b>{e(la)}</p><p><b class="tb">{e(b)}</b>{e(lb)}</p></section>""" for c, lead, la, lb in champs)
    summ_html = "".join(f'<h3>{e(t)}</h3><ul>{"".join(f"<li>{e(x)}</li>" for x in lines)}</ul>' for t, lines in summ)
    best_html = "".join(f'<li>{chip(c)}<span class="wr">{round(w / n * 100)}%</span><span class="rec">{w}勝{n - w}敗</span></li>' for c, n, w in best)
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(a)} vs {e(b)} 選角數據分析</title>{f'<link rel="icon" type="image/png" href="{FAVICON}">' if FAVICON else ""}
<style>
:root {{ --bg:#f3f5f7; --surface:#fff; --line:#dde2e8; --ink:#141a22; --muted:#5d6877; --a:#0089a0; --b:#7a5cc8; --good:#1f7a3d; --accent-soft:#d8eef0 }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f1419; --surface:#171e26; --line:#2a333e; --ink:#e6ebf0; --muted:#94a0ae; --a:#1f9fac; --b:#9a80e6; --good:#6fd08f; --accent-soft:#163a40 }} }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.6 "Noto Sans TC","PingFang TC",system-ui,sans-serif }}
main {{ max-width:860px; margin:0 auto; padding:24px 16px 32px }}
.eyebrow {{ font-size:12px; color:var(--muted); letter-spacing:.04em }}
h1 {{ margin:4px 0 2px; font-size:30px }} h1 .ta {{ color:var(--a) }} h1 .tb {{ color:var(--b) }}
.sub {{ color:var(--muted); font-size:13px; margin:0 0 18px }}
.card {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:14px 16px; margin-bottom:12px }}
.card h2 {{ margin:0 0 10px; font-size:18px }}
.ch {{ display:inline-flex; align-items:center; gap:5px; margin:2px 8px 2px 0; white-space:nowrap }}
.ch img {{ border-radius:5px }} .ch b {{ font-size:12px; color:var(--muted) }}
ol {{ margin:0; padding-left:20px }} li {{ margin:4px 0 }} .wr {{ font-weight:700; color:var(--good); margin:0 6px }} .rec {{ color:var(--muted); font-size:13px }}
.row {{ display:grid; grid-template-columns:64px 1fr; gap:8px; align-items:start; padding:6px 0; border-top:1px solid var(--line) }} .row:first-of-type {{ border-top:0 }}
.ta {{ color:var(--a) }} .tb {{ color:var(--b) }} .row > b {{ padding-top:4px }}
.grp {{ display:inline-flex; flex-wrap:wrap; align-items:center; margin-right:10px }} .grp i {{ font-style:normal; font-size:12px; color:var(--muted); margin-left:2px }}
.more {{ font-size:12px; color:var(--muted) }}
.champs {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,380px),1fr)); gap:10px }}
.champ {{ border:1px solid var(--line); border-radius:10px; padding:10px 12px }} .champ h3 {{ margin:0 0 4px; font-size:16px }}
.champ p {{ margin:3px 0; font-size:14px }} .champ p b {{ display:inline-block; min-width:52px }}
.champ .lead {{ background:var(--accent-soft); border-radius:6px; padding:2px 8px; font-size:13px }}
.summ h3 {{ margin:12px 0 4px; font-size:15px; color:var(--a) }} .summ h3:first-of-type {{ margin-top:0 }}
.summ ul {{ margin:0; padding-left:20px }} .summ li {{ margin:3px 0; font-size:14px }}
footer {{ color:var(--muted); font-size:12px; margin-top:8px }}
.top {{ display:flex; justify-content:flex-end; margin-bottom:6px }}
.home {{ display:inline-flex; align-items:center; gap:8px; color:var(--ink); text-decoration:none; font-weight:700; font-size:14px;
  background:var(--surface); border:1px solid var(--line); border-radius:999px; padding:4px 12px 4px 4px }}
.home img {{ width:26px; height:26px; border-radius:6px }} .home:hover {{ border-color:var(--a); color:var(--a) }}
</style></head><body><main>
<div class="top"><a class="home" href="{e(home)}" title="回到 LoL2026世界賽分析 首頁">{f'<img src="{FAVICON}" alt="">' if FAVICON else ""}LoL2026世界賽分析</a></div>
<div class="eyebrow">{e(rname)} · {e(mid)}</div>
<h1><span class="ta">{e(a)}</span> vs <span class="tb">{e(b)}</span></h1>
<p class="sub">觀賽前的選角數據分析 · {e(a)} {A[0]} 局、{e(b)} {B[0]} 局的 BP 統計；勝率皆為該隊在那些局的戰績</p>
<div class="card summ"><h2>賽事總結</h2>{summ_html}</div>
<div class="card"><h2>當前賽事勝率最高前三 <small class="rec">（至少選用 3 次）</small></h2><ol>{best_html}</ol></div>
<div class="card"><h2>被ban前三</h2><div class="row"><b class="ta">{e(a)}</b><div>{groups(a, "banned", "被ban")}</div></div><div class="row"><b class="tb">{e(b)}</b><div>{groups(b, "banned", "被ban")}</div></div></div>
<div class="card"><h2>ban前三</h2><div class="row"><b class="ta">{e(a)}</b><div>{groups(a, "ban", "ban")}</div></div><div class="row"><b class="tb">{e(b)}</b><div>{groups(b, "ban", "ban")}</div></div></div>
<div class="card"><h2>值得注意的選角</h2><div class="champs">{rows}</div></div>
<footer>資料整理於 {e(W['collected'])} · 賽果與 BP 取自 gol.gg／Leaguepedia／Liquipedia · 選手數據取自 gol.gg（無法連線的場次用 Leaguepedia）</footer>
</main></body></html>
"""


def main():
    out_dir = f"{data_dir}/analysis"
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for ri, rnd in enumerate(W["rounds"]):
        if rnd["status"] == "done":
            continue
        for k, m in enumerate(rnd["matches"]):
            if m.get("winner"):
                continue
            mid, a, b = f"r{ri + 1}-m{k + 1}", m["a"], m["b"]
            res = analyse(a, b)
            res = (*res, summary(a, b, res[0], res[1], mid))
            stem = f"{mid}_{a}_vs_{b}"
            # the site copy links home to the main page; the exported copy to that day's dated snapshot
            open(f"{out_dir}/{stem}.html", "w").write(as_html(a, b, mid, rnd["name"], *res, "../worlds2026_analysis.html"))
            if export:
                os.makedirs(f"{export}/analysis", exist_ok=True)
                open(f"{export}/analysis/{stem}.html", "w").write(as_html(a, b, mid, rnd["name"], *res, f"../worlds2026_{TODAY}.html"))
            if export:
                open(f"{export}/{stem}.txt", "w").write(as_text(a, b, mid, *res))
            made.append((mid, stem))
        break   # only the round in progress
    json.dump(dict(made), open(f"{out_dir}/index.json", "w"), ensure_ascii=False, indent=1)
    print("\n".join(f"{mid}: {stem}" for mid, stem in made))


if __name__ == "__main__":
    main()
