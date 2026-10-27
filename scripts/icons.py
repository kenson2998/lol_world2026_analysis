"""Build champion-name -> data-URI icon map from Riot Data Dragon (inlined because the report can't load remote images).

usage: python3 -I icons.py data_dir [cache_dir]
writes data_dir/champ_icons.json
"""
import base64, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

DD = "https://ddragon.leagueoflegends.com"
SIZE = "48"


def curl(url, dest=None):
    cmd = ["curl", "-s", "--max-time", "30", url] + (["-o", dest] if dest else [])
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def main(data_dir, cache):
    os.makedirs(cache, exist_ok=True)
    ver = json.loads(curl(f"{DD}/api/versions.json"))[0]
    champs = json.loads(curl(f"{DD}/cdn/{ver}/data/en_US/champion.json"))["data"]

    def icon(item):
        key, info = item
        src, small = f"{cache}/{key}.png", f"{cache}/{key}_{SIZE}.png"
        if not os.path.exists(small):
            curl(f"{DD}/cdn/{ver}/img/champion/{key}.png", src)
            subprocess.run(["sips", "-Z", SIZE, src, "--out", small], capture_output=True, check=True)
        return info["name"], "data:image/png;base64," + base64.b64encode(open(small, "rb").read()).decode()

    with ThreadPoolExecutor(8) as ex:
        icons = dict(ex.map(icon, champs.items()))
    # Taiwan-server (zh_TW) names keyed by the English display name
    zh = json.loads(curl(f"{DD}/cdn/{ver}/data/zh_TW/champion.json"))["data"]
    names_zh = {info["name"]: zh[key]["name"] for key, info in champs.items() if key in zh}
    json.dump({"version": ver, "icons": icons, "zh_TW": names_zh}, open(f"{data_dir}/champ_icons.json", "w"), ensure_ascii=False)
    print(f"{len(icons)} icons from Data Dragon {ver}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(sys.argv[1], ".icon_cache"))
