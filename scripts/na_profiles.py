"""In-game profile icon (and level) of every NA account in soloq_na.json, from OP.GG's summoner profile.
The icon is inlined as a data URI so the page doesn't hotlink OP.GG.

usage: python3 -I na_profiles.py data_dir
writes data_dir/na_profiles.json: {"NA:name#tag": {"icon": "data:image/...", "level": n, "url": "<OP.GG image url>"}}
"""
import base64, json, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from soloq import call

SIZE = 96   # px; shown at 44px, so this stays sharp on 2x screens

PROFILE_RE = re.compile(r'Summoner\("(?:[^"\\]|\\.)*","(?:[^"\\]|\\.)*","([^"]*)",(\d+|null)\)')


def profile(acct):
    name, tag = acct[3:].rsplit("#", 1)
    text, is_err = call("lol_get_summoner_profile", {"game_name": name, "tag_line": tag, "region": "NA",
                                                     "desired_output_fields": ["data.summoner.{game_name,tagline,profile_image_url,level}"]})
    m = None if is_err else PROFILE_RE.search(text)
    if not m:
        return acct, None
    url = m.group(1).replace("\\/", "/")
    img = subprocess.run(["curl", "-s", "--max-time", "30", url], capture_output=True).stdout
    if not img:
        return acct, None
    # OP.GG serves large originals; shrink to SIZE px JPEG with macOS sips so the inlined page stays small
    with tempfile.TemporaryDirectory() as d:
        src, dst = f"{d}/in", f"{d}/out.jpg"
        open(src, "wb").write(img)
        r = subprocess.run(["sips", "-Z", str(SIZE), "-s", "format", "jpeg", "-s", "formatOptions", "80", src, "--out", dst],
                           capture_output=True)
        if r.returncode == 0 and os.path.exists(dst):
            img = open(dst, "rb").read()
    mime = "image/png" if img[:4] == b"\x89PNG" else "image/jpeg"
    return acct, {"icon": f"data:{mime};base64," + base64.b64encode(img).decode(), "url": url,
                  "level": int(m.group(2)) if m.group(2).isdigit() else None}


def main(data_dir):
    na = json.load(open(f"{data_dir}/soloq_na.json"))
    accts = sorted({a for p in na["players"] for a in p.get("all_accounts", []) if a.startswith("NA:")})
    with ThreadPoolExecutor(8) as ex:
        got = dict(ex.map(profile, accts))
    out = {a: v for a, v in got.items() if v}
    for a in accts:
        print(f'{a:40} {"ok  lv " + str(out[a]["level"]) if a in out else "no profile"}', file=sys.stderr)
    json.dump(out, open(f"{data_dir}/na_profiles.json", "w"), ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
