"""Debug helper: call a signed scoregg endpoint and print a compact view of the response.

usage: python3 -I scoregg_probe.py /services/path.php '{"param":"v"}' [chars]
"""
import json, os, subprocess, sys

JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scoregg.js")


def call(api, params=None):
    out = subprocess.run(["node", JS, api, json.dumps(params or {})], capture_output=True, text=True).stdout
    return json.loads(out)


if __name__ == "__main__":
    d = call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
    print(d.get("code"), d.get("message"))
    print(json.dumps(d.get("data"), ensure_ascii=False)[:n])
