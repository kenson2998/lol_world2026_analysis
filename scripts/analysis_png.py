"""Render each pre-match analysis page (data/analysis/*.html from match_analysis.py) to a PNG.

usage: python3.11 analysis_png.py data_dir export_dir      (needs playwright)
"""
import json, os, sys
from playwright.sync_api import sync_playwright

data_dir, export = sys.argv[1], sys.argv[2]
pages = json.load(open(f"{data_dir}/analysis/index.json"))
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 800}, device_scale_factor=2, color_scheme="light")
    for mid, stem in pages.items():
        page.goto("file://" + os.path.abspath(f"{data_dir}/analysis/{stem}.html"))
        page.wait_for_timeout(300)
        page.screenshot(path=f"{export}/{stem}.png", full_page=True)
        print(f"{mid}: {export}/{stem}.png")
    browser.close()
