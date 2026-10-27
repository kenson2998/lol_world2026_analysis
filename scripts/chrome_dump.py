"""Render a page in headless Chrome (runs its JS, e.g. Cloudflare checks) and save the resulting DOM.

usage: python3 -I chrome_dump.py out.html url [wait_ms]
"""
import subprocess, sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
out, url = sys.argv[1], sys.argv[2]
wait = sys.argv[3] if len(sys.argv) > 3 else "15000"
res = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-blink-features=AutomationControlled",
                      "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
                      f"--virtual-time-budget={wait}", "--dump-dom", url], capture_output=True, text=True, timeout=120)
open(out, "w").write(res.stdout)
print(len(res.stdout), "bytes;", res.stderr.strip()[-300:])
