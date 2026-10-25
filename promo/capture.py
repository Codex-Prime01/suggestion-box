"""
Measure the real UI for the promo, using a THROWAWAY database (never your real one).

    python promo/capture.py <throwaway-dir>

Writes promo/ui.json (sizes, radii, colours, copy) and promo/ref/*.png (reference shots).
Only fake demo data is used.
"""
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(sys.argv[1]).resolve()
TMP.mkdir(parents=True, exist_ok=True)
PORT = 8767
env = {**os.environ, "DATABASE_URL": f"sqlite:///{(TMP / 'promo.sqlite3').as_posix()}", "DEBUG": "True"}
py = sys.executable


def manage(*args):
    subprocess.run([py, "manage.py", *args], cwd=ROOT, env=env, check=True, capture_output=True)


manage("migrate")
manage("createcachetable")

# Open the box with a demo key (public key only; the browser never needs the private one for the drop page)
setup = r"""
import base64, json
from nacl.public import PrivateKey, SealedBox
from box.models import BoxSettings
sk = PrivateKey.generate()
box = BoxSettings.load()
box.public_key = base64.b64encode(bytes(sk.public_key)).decode()
box.encrypted_private_key = base64.b64encode(b"x" * 72).decode()
box.key_salt = base64.b64encode(b"s" * 16).decode()
box.is_open = True
box.save()
# Real ciphertext for bar 5, made exactly like the browser does it (libsodium sealed box)
payload = {"v": 1, "name": "", "rank": "", "service_number": "", "unit": "Alpha Coy",
           "phone": "", "body": "The water tank in block C has been leaking for three weeks."}
print(base64.b64encode(SealedBox(sk.public_key).encrypt(json.dumps(payload).encode())).decode())
"""
ct = subprocess.run([py, "manage.py", "shell", "-c", setup], cwd=ROOT, env=env, check=True,
                    capture_output=True, text=True).stdout.strip().splitlines()[-1]

server = subprocess.Popen([py, "manage.py", "runserver", str(PORT), "--noreload"], cwd=ROOT, env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    from playwright.sync_api import sync_playwright
    import urllib.request
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/drop/"); break
        except Exception:
            time.sleep(0.5)

    MEASURE = """sel => { const e = document.querySelector(sel); if (!e) return null;
      const r = e.getBoundingClientRect(), c = getComputedStyle(e);
      return {x: r.x, y: r.y, w: r.width, h: r.height, radius: c.borderRadius, bg: c.backgroundColor,
              color: c.color, font: c.fontSize + ' ' + c.fontWeight, text: (e.innerText || e.placeholder || '').trim().slice(0, 120)}; }"""
    ui = {"ciphertext": ct}
    ref = ROOT / "promo" / "ref"
    ref.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
        page.goto(f"http://127.0.0.1:{PORT}/drop/", wait_until="networkidle")
        vars_ = page.evaluate("""() => { const c = getComputedStyle(document.body);
          return Object.fromEntries(['--bg','--text','--muted','--card','--card-border','--accent','--accent-text','--chip']
            .map(k => [k, c.getPropertyValue(k).trim()])); }""")
        ui["theme"] = vars_
        ui["step1"] = {k: page.evaluate(MEASURE, s) for k, s in {
            "form": "#drop-form", "header": "header h1", "sub": "header p", "label": "#step-label",
            "unitLabel": "label[for=unit]", "unit": "#unit", "hint": "#step-1 > p", "name": "#sender_name",
            "next": "#to-step-2", "backBtn": "header a"}.items()}
        page.screenshot(path=str(ref / "drop-step1.png"))
        page.fill("#unit", "Alpha Coy")
        page.click("#to-step-2")
        page.wait_for_timeout(300)
        ui["step2"] = {k: page.evaluate(MEASURE, s) for k, s in {
            "form": "#drop-form", "label": "#step-label", "fromChip": "#from-chip", "chip": ".choice",
            "body": "#body", "photos": "label[for=photos]", "photoHint": "#step-2 p.text-xs",
            "lockNote": "#step-2 > .chip.text-xs", "submit": "button[type=submit]", "back": "#to-step-1"}.items()}
        ui["categories"] = page.eval_on_selector_all(".choice", "els => els.map(e => e.innerText.trim())")
        page.screenshot(path=str(ref / "drop-step2.png"))
        page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle")
        page.evaluate("document.getAnimations().forEach(a => a.finish())")
        page.screenshot(path=str(ref / "intro.png"))
        b.close()
    (ROOT / "promo" / "ui.json").write_text(json.dumps(ui, indent=2), encoding="utf-8")
    print("wrote promo/ui.json and promo/ref/*.png")
finally:
    server.terminate()
