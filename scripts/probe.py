"""Debug helper: show raw OP.GG pro lookups for given players across regions.

usage: python3 -I probe.py REGION[,REGION] name [name ...]
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soloq

for nick in sys.argv[2:]:
    for region in sys.argv[1].split(","):
        text, err = soloq.call("lol_get_pro_player_riot_id",
                               {"player_name": nick, "region": region, "return_suggestions": True})
        try:
            d = json.loads(text)
            p = (d.get("data") or {}).get("player") or {}
            sugg = [(s.get("nickname"), (s.get("team") or {}).get("short_name"), (s.get("riot_id") or {}).get("full"))
                    for s in (d.get("suggestions") or (d.get("data") or {}).get("suggestions") or [])][:5]
            print(f"{nick:10} {region:4} -> {p.get('nickname')} [{(p.get('team') or {}).get('short_name')}] "
                  f"{(p.get('riot_id') or {}).get('full')} | sugg={sugg}")
        except ValueError:
            print(f"{nick:10} {region:4} RAW {text[:200]!r}")
