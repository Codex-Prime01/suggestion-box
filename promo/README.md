# Promo video

A 16-second promo for Suggestion Box, built from the real UI. Dev-only: nothing here is part of the website.
The brief is `docs/prompts/intro-promo-video.md`.

## Files
| File | What it is |
|---|---|
| `promo.html` | The film. Every frame is computed from time in `window.seek(t)`. Add `?mode=v` for the vertical cut. Open it through a local server to watch it play |
| `audio.html` | The soundtrack, composed in code (120 BPM) |
| `capture.py` | Measures the real drop form into `ui.json` and `ref/`, using a throwaway database |
| `render.py` | Renders everything into `out/` (git-ignored) |

## Make it
Needs Playwright (`pip install playwright` then `python -m playwright install chromium`) and ffmpeg on PATH.
```powershell
python promo/render.py beats      # one frame per beat in out/beats/. Look at these first
python promo/render.py audio
python promo/render.py full       # out/suggestion-box-promo.mp4
python promo/render.py vertical   # out/suggestion-box-promo-vertical.mp4
python promo/render.py loop       # out/hero-loop.webm
```

## Storyboard (120 BPM: a beat is 0.5 s, a bar is 2 s)
The through-line object is **the note**. It is the only thing in the accent colour, plus one key word per scene.

| Bar | Time | The note is… | What happens | Big type |
|---|---|---|---|---|
| 1 | 0–2 | a paper note | "Speaking / up / feels / risky" land on beats 1–4. The note slides in at 1.75 and knocks "risky" out | (hook) |
| 2 | 2–4 | the form card, then the Next button | Note unfolds into the card, collapses into Next and uncovers the form. Cursor types "Alpha Coy", clicks Next at 3.5 | Only your **unit** is required |
| 3 | 4–6 | the "Welfare" chip | Click Welfare at 4.0, message types 4.5–5.4, photo attaches at 5.5, location pin wiped by a mask at 5.75 | Location **removed** |
| 4 | 6–8 | the Drop button, a sealed note, the padlock | Click Drop at 6.0, card folds away, box rises, note drops at 6.5, shackle snaps at 7.0 | **Locked** on your phone |
| 5 | 8–10 | one line of real ciphertext | The padlock stretches into a highlighted line of ciphertext from the app's own encryption. It scrolls | We **can't** read it either |
| 6 | 10–12 | the owner's padlock | Dark wipe, passphrase dots fill, lock opens at 10.75, inbox rows unscramble left to right | **Only** the CO |
| 7 | 12–14 | the status pill | Payoff on 12.0: status flips to "✓ Resolved", extra camera push, private note types | **Heard** |
| 8 | 14–16 | the logo | The pill becomes the logo's lock body, shackle draws, name + promise + "link coming soon". Last half-beat fades to black | |

## Changing it
- Timings live in `promo.html`: `noteKeys()` (the note), `CAM` (camera), `CAPS` (big type), `LABELS`, `CLICKS`.
- If you move an event, move its sound in `audio.html` (`SWOOSH`, `CLICK`, the `hit` calls) too.
- The end card says "link coming soon". Put the real URL in `#eL` once the site is live.
- The hero loop's seam is a half-second blend (the only crossfade), so it loops without a jump.
