"""Debug helper: fetch URLs with a browser UA, save them, and print status/size plus a text excerpt.

usage: python3 -I fetch_probe.py out_dir url [url ...]
"""
import hashlib, os, re, subprocess, sys

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"
out_dir = sys.argv[1]
for url in sys.argv[2:]:
    path = os.path.join(out_dir, hashlib.md5(url.encode()).hexdigest()[:8] + ".html")
    code = subprocess.run(["curl", "-s", "-L", "--max-time", "30", "-A", UA, "-o", path, "-w", "%{http_code}", url],
                          capture_output=True, text=True).stdout
    body = open(path, errors="ignore").read() if os.path.exists(path) else ""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)))
    print(f"{code} {len(body):>8} {path} {url}\n    {text[:300]}")
