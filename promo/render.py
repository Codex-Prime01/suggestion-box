"""
Render the promo.  Needs: playwright (+ chromium) and ffmpeg on PATH.  Dev-only, not part of the site.

    python promo/render.py beats     # one frame per beat + scene boundaries -> promo/out/beats/ (look at these first)
    python promo/render.py audio     # soundtrack -> promo/out/soundtrack.wav
    python promo/render.py full      # 1920x1080 60fps with motion blur -> promo/out/suggestion-box-promo.mp4
    python promo/render.py vertical  # 1080x1920 cut -> promo/out/suggestion-box-promo-vertical.mp4
    python promo/render.py loop      # promo/out/hero-loop.webm (bars 4-6, muted, 6 s)
"""
import base64
import contextlib
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "promo" / "out"
PORT = 8790
FPS, SUB, DUR = 60, 3, 16.0


@contextlib.contextmanager
def server():
    p = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", str(ROOT)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/promo/promo.html"); break
            except Exception:
                time.sleep(0.2)
        yield f"http://127.0.0.1:{PORT}/promo/"
    finally:
        p.terminate()


def open_page(p, mode, scale=1.0):
    w, h = (1080, 1920) if mode == "v" else (1920, 1080)
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    return b, page, errors


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg not found on PATH. Install it (winget install Gyan.FFmpeg) and open a new terminal.")
    return exe


def run_ff(*args):
    # -nostdin: otherwise ffmpeg waits for keyboard input when run from a script and hangs
    subprocess.run([ffmpeg(), "-nostdin", "-y", "-loglevel", "error", *map(str, args)], check=True)


def beats():
    d = OUT / "beats"
    d.mkdir(parents=True, exist_ok=True)
    times = sorted({round(i * 0.5, 2) for i in range(32)} | {round(i * 0.5 + 0.25, 2) for i in range(32)} | {15.9})
    with server() as base, sync_playwright() as p:
        for mode in ("h", "v"):
            b, page, errors = open_page(p, mode, 0.5)
            page.goto(base + f"promo.html?mode={mode}")
            for t in times:
                page.evaluate("t => window.seek(t)", t)
                page.screenshot(path=str(d / f"{mode}_{t:05.2f}.png"))
            print(mode, "frames:", len(times), "errors:", errors or "none")
            b.close()


def audio():
    OUT.mkdir(parents=True, exist_ok=True)
    with server() as base, sync_playwright() as p:
        b, page, errors = open_page(p, "h")
        page.goto(base + "audio.html")
        b64 = page.evaluate("() => window.renderWav()")
        (OUT / "soundtrack_raw.wav").write_bytes(base64.b64decode(b64))
        b.close()
        print("errors:", errors or "none")
    # loudness: -14 LUFS, true peak -1 dBTP
    run_ff("-i", OUT / "soundtrack_raw.wav", "-af", "loudnorm=I=-14:TP=-1:LRA=11", "-ar", "48000", OUT / "soundtrack.wav")
    print("wrote", OUT / "soundtrack.wav")


def video(mode):
    OUT.mkdir(parents=True, exist_ok=True)
    w, h = (1080, 1920) if mode == "v" else (1920, 1080)
    name = "suggestion-box-promo" + ("-vertical" if mode == "v" else "")
    silent = OUT / f"{name}-silent.mp4"
    # 3 subframes per frame (t - 1/240, t, t + 1/240) piped in at 180 fps, averaged by tmix, then every 3rd kept -> 60 fps
    ff = subprocess.Popen([
        ffmpeg(), "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS * SUB), "-c:v", "mjpeg", "-i", "-",
        "-vf", f"tmix=frames={SUB}:weights='1 1 1',select='eq(mod(n\\,{SUB})\\,{SUB - 1})',setpts=N/{FPS}/TB,scale=out_range=tv,format=yuv420p",
        # JPEG frames are full-range; convert to standard (tv) range so every player shows the right colours
        "-r", str(FPS), "-pix_fmt", "yuv420p", "-color_range", "tv", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-s", f"{w}x{h}", str(silent)],
        stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    t0 = time.time()
    with server() as base, sync_playwright() as p:
        b, page, errors = open_page(p, mode)
        page.goto(base + f"promo.html?mode={mode}")
        for i in range(n):
            for k in (-1, 0, 1):
                t = min(DUR - 1e-3, max(0.0, i / FPS + k / (FPS * 4)))
                page.evaluate("t => window.seek(t)", t)
                ff.stdin.write(page.screenshot(type="jpeg", quality=92))
            if i % 120 == 0:
                print(f"{mode}: frame {i}/{n}  ({time.time() - t0:.0f}s)", flush=True)
        b.close()
    ff.stdin.close()
    ff.wait()
    if errors:
        print("page errors:", errors)
    wav = OUT / "soundtrack.wav"
    final = OUT / f"{name}.mp4"
    run_ff("-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final)
    silent.unlink()
    print("wrote", final)


def loop():
    src = OUT / "suggestion-box-promo.mp4"
    dst = OUT / "hero-loop.webm"
    # bars 4-6 (6-12 s). The seam: the last half second (11.5-12) blends with the half second just before
    # bar 4 (5.5-6), so the loop ends exactly where it starts. Nothing from bar 7 leaks in.
    fc = ("[0:v]trim=5.5:12,setpts=PTS-STARTPTS,scale=960:540,fps=30,split[a][b];"
          "[a]trim=0.5:6.5,setpts=PTS-STARTPTS[main];[b]trim=0:0.5,setpts=PTS-STARTPTS[head];"
          "[main][head]xfade=transition=fade:duration=0.5:offset=5.5,format=yuv420p[v]")  # 4:2:0 so every browser plays it
    for crf in (36, 40, 44):
        run_ff("-i", src, "-filter_complex", fc, "-map", "[v]", "-an",
               "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", crf, "-row-mt", "1", "-deadline", "good", dst)
        size = dst.stat().st_size
        print(f"crf {crf}: {size / 1e6:.2f} MB")
        if size < 1.5e6:
            break
    print("wrote", dst)
    # MP4 fallback (older iPhones/Safari) and a poster so the hero never shows an empty box
    mp4 = OUT / "hero-loop.mp4"
    run_ff("-i", dst, "-c:v", "libx264", "-preset", "slow", "-crf", "28", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "-an", mp4)
    run_ff("-i", dst, "-frames:v", "1", "-q:v", "4", OUT / "hero-poster.jpg")
    # copy into the site
    site = ROOT / "static" / "video"
    site.mkdir(exist_ok=True)
    for f in (dst, mp4, OUT / "hero-poster.jpg"):
        shutil.copy2(f, site / f.name)
        print(f"static/video/{f.name}: {f.stat().st_size / 1e3:.0f} KB")


if __name__ == "__main__":
    {"beats": beats, "audio": audio, "full": lambda: video("h"), "vertical": lambda: video("v"), "loop": loop}[sys.argv[1]]()
