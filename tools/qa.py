"""Quality checks for the built site. Needs Playwright with Chromium (only for screenshots and console checks).

Checks: every internal link resolves; every page carries the concept label; no em or en dashes and no
three-hyphen lines; common US spellings; console errors at desktop and phone widths; text present with
JavaScript switched off. Saves screenshots to qa/.
Run: python3 tools/qa.py
"""
import re
import sys
import threading
import http.server
import functools
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOTS = ROOT / "qa"
SHOTS.mkdir(exist_ok=True)
problems = []

pages = sorted(DOCS.glob("*.html"))
for p in pages:
    t = p.read_text()
    if "Not a Razorpay product" not in t:
        problems.append(f"{p.name}: concept label missing")
    for bad in ("\u2014", "\u2013"):  # em and en dash
        if bad in t:
            problems.append(f"{p.name}: dash character {bad!r} found")
    if re.search(r"(^|\n)\s*---\s*(\n|$)", t):
        problems.append(f"{p.name}: three-hyphen line")
    text = re.sub(r"<[^>]+>", " ", t)
    text = text.replace("Optimizer", "")  # Razorpay's product name, not a spelling
    for us in ("color", "behavior", "favor", "center", "organiz", "prioritiz", "recogniz", "analyz", "optimiz", "catalog ", "license ", "canceled"):
        if re.search(rf"\b{us}", text, re.I):
            problems.append(f"{p.name}: possible US spelling '{us}'")
    for href in re.findall(r'href="([^"#]+)"', t):
        if href.startswith(("http://", "https://", "mailto:", "data:")):
            continue
        if not (DOCS / href).exists():
            problems.append(f"{p.name}: broken link {href}")

for f in (DOCS / "downloads").glob("*"):
    if "\u2014" in f.read_text() or "\u2013" in f.read_text():
        problems.append(f"{f.name}: dash character")

# Serve the site and drive Chromium
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))
server = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
handler.log_message = lambda *a, **k: None

from playwright.sync_api import sync_playwright  # noqa: E402

KEY = ["index.html", "item-sl-1039.html", "item-sl-1043.html", "item-sl-1047.html", "item-edf-pack.html", "item-sl-1052-1053.html",
       "item-sl-1043-done.html", "invoices.html", "declarations.html", "playbook.html", "results.html",
       "learning.html", "controls.html", "how-it-works.html", "item-sl-1044.html", "judges.html", "rules-only.html"]
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for name, vp in (("desktop", {"width": 1280, "height": 900}), ("phone", {"width": 390, "height": 844})):
        ctx = browser.new_context(viewport=vp, device_scale_factor=1)
        page = ctx.new_page()
        errors = []
        # resource failures (for example web fonts blocked by a proxy) are not site errors; internal links are checked above
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and not m.text.startswith("Failed to load resource") else None)
        page.on("pageerror", lambda ex: errors.append(str(ex)))
        for p in pages:
            page.goto(f"http://127.0.0.1:8765/{p.name}")
            page.wait_for_load_state("networkidle")
            # horizontal overflow of the page itself
            over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if over > 1:
                problems.append(f"{name} {p.name}: page scrolls sideways by {over}px")
            # labels squeezed to nothing (the Controls defect at phone width)
            narrow = page.evaluate("Array.from(document.querySelectorAll('.setting > div:first-child, .row .main, .kv li b')).filter(function(el){return el.getBoundingClientRect().width < 60}).length")
            if narrow:
                problems.append(f"{name} {p.name}: {narrow} label block(s) narrower than 60px")
            if p.name in KEY:
                page.screenshot(path=str(SHOTS / f"{name}-{p.stem}.png"), full_page=True)
        if errors:
            problems.append(f"{name}: console errors: {errors[:5]}")
        ctx.close()
    # JavaScript off: text still there
    ctx = browser.new_context(java_script_enabled=False)
    page = ctx.new_page()
    page.goto("http://127.0.0.1:8765/index.html")
    body = page.inner_text("main")
    if "Ready for your OK" not in body.replace("READY FOR YOUR OK", "Ready for your OK") or "lakh" not in body:
        problems.append("JS off: home page text missing")
    ctx.close()
    # Interactions with JavaScript on
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.goto("http://127.0.0.1:8765/item-sl-1043.html")
    page.click("text=Edit draft")
    if page.get_attribute("#draft-sl-1043", "contenteditable") != "true":
        problems.append("Edit draft did not switch on editing")
    page.click("text=Not now")
    if "snoozes" not in page.inner_text("#note-sl-1043"):
        problems.append("Not now note did not appear")
    page.click("text=Approve note")
    page.wait_for_load_state("load")
    if "item-sl-1043-done.html" not in page.url:
        problems.append("Approve did not go to the done page")
    page.goto("http://127.0.0.1:8765/controls.html")
    page.click(".setting .toggle")
    if "show" not in (page.get_attribute("#settings-note", "class") or ""):
        problems.append("Settings note did not show")
    # approval state: the done page marks the item and Today moves it
    page.goto("http://127.0.0.1:8765/index.html")
    moved = page.evaluate("document.querySelector('ul.list[data-bucket=done] .row') ? 1 : 0")
    if not moved:
        problems.append("Approved item did not move to Done this morning")
    page.click("text=Reset the demo")
    page.wait_for_load_state("networkidle")
    if page.evaluate("document.querySelector('ul.list[data-bucket=done] .row') ? 1 : 0"):
        problems.append("Reset the demo did not clear the approval")
    # dark scheme screenshots of two pages
    dctx = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="dark")
    dpage = dctx.new_page()
    for n in ("index.html", "item-sl-1043.html"):
        dpage.goto(f"http://127.0.0.1:8765/{n}")
        dpage.screenshot(path=str(SHOTS / f"phone-dark-{n[:-5]}.png"), full_page=True)
    dctx.close()
    ctx.close()
    browser.close()
server.shutdown()

print(f"{len(pages)} pages checked")
if problems:
    print("PROBLEMS:")
    for x in problems:
        print(" -", x)
    sys.exit(1)
print("All checks passed")
