# Intro promo video — the prompt

Paste everything inside the box below into Claude Code **from the project folder** (so it can run the app, read the templates and capture the real UI).

What changed from the two original prompts:
- **Merged into one plan.** UI-rebuilt-as-vectors (prompt 2) is the main language. Real footage (prompt 1) becomes optional, because we have no clips we own and we must not show real soldiers.
- **Contradictions fixed.** "Springs" vs "no bouncy easing": critically damped springs, at most 3% overshoot. "No crossfades" vs "fade to black": only the final half-beat fades.
- **Defaults filled in from this project**, so it can build without stopping to ask.
- **Safety rules added:** fake demo data only, no real names/units/faces/insignia, never invent features or numbers.
- **Tied to the site:** an optional 6-second muted loop for the intro page hero.

---

```text
<context>
You are in the Suggestion Box repo (Django). It's a private, encrypted suggestion box for a military unit:
soldiers drop a complaint/suggestion (unit required, everything else optional, up to 3 photos), it is
encrypted on their phone, and only the box owner (the commanding officer) can unlock it.
Read CLAUDE.md, docs/01-project-brief.md and docs/03-architecture.md first. Only show features that
really exist in the code. Never invent features, numbers, users or testimonials.
</context>

<inputs>
Ask me ONLY for things I haven't given and that have no default. Defaults:
- Product name: "Suggestion Box" (or BoxSettings.title if set)
- One-line promise: "Say it straight. It stays sealed"   (no full stops on screen; drop them)
- Accent colour: #c8b35a (the camo theme accent). Background #2f3a24 / near-black #141a0f. Text #f1f3ea
- Typeface: Saira (static/fonts, woff2, already in the repo). One typeface only. Tight tracking (-0.03em) on big type
- Logo: static/icons/icon.svg (box + padlock)
- UI: capture it yourself. Run the app locally, create the owner, 2FA, key, then `python manage.py seed_demo`
  for FAKE messages. Use only seed data. Never type real names, real unit names or phone numbers
- Music: compose it in code (Web Audio API, OfflineAudioContext), 120 BPM. If I give you a royalty-free track
  instead (e.g. Mixkit, free for commercial use), analyse it as described in <build>
- Real video clips: optional. Only clips I own and confirm are cleared. No people in uniform, no faces, no insignia
- End card link: leave a clean placeholder line "link coming soon" until I give you the live URL
</inputs>

<through_line>
The through-line object is THE NOTE (the folded paper from the intro page hero, static/css/intro.css +
templates/box/intro.html). It starts in the UI and changes role in every scene:
note -> the form card -> the "Drop it in the box" button -> the sealed note dropping into the slot ->
the padlock -> the scrambled text the server sees -> the unlocked message -> the logo on the end card.
Name it in your storyboard and show which shape it takes in each scene. Only the note and ONE key word per
scene use the accent colour.
</through_line>

<direction>
High-end minimal, 16 seconds, 1920x1080. One idea per shot, lots of empty space.
Rebuild the real UI as vector/DOM layers so parts move on their own. Never slide a flat screenshot in.
Measure the real UI (sizes, radii, colours) from the running app so it matches.
A cursor drives every interaction with real clicks and typing. The camera zooms screen-studio style so each
moment fills the frame. It never sits still: push 1.00 -> 1.04 across a scene, and each scene starts at the zoom
the previous one ended on.
Motion: critically damped springs (max 3% overshoot) and exponential ease-outs, written as functions of time.
Nothing appears from nothing: it grows, unfolds or is revealed by a mask. Masked type reveals, match cuts.
Something changes on every beat. No hold longer than half a second. No full stops in on-screen text.
Banned: particle bursts, shockwave rings, glows/neon, lens flares, camera shake, RGB split, grid floors,
flashing backgrounds, generic gradients, crossfades (except the final fade to black), bouncy easing,
placeholder cards, stock-looking templates, anything military-dramatic (explosions, guns, flags waving).
</direction>

<structure>
120 BPM = 0.5 s per beat, 2 s per bar, 8 bars. Every cut on a downbeat, every UI hit on a beat.
Start from this beat sheet. Refine it after you capture the UI, then show me the final timed storyboard.

Bar 1  0-2s    HOOK. "Speaking up feels risky" lands word by word on beats 1-4. On beat 4 the note slides
               in from the right and pushes "risky" out of frame
Bar 2  2-4s    The note unfolds into the drop form, step 1. Cursor types a fake unit ("Alpha Coy") on
               beats 1-2, clicks Next on beat 4. Key word: "Only your unit is required"
Bar 3  4-6s    Step 2. Cursor clicks the "Welfare" chip (beat 1), message types (beats 2-3), a photo
               attaches (beat 4). A location pin on the photo is wiped away by a mask: "Location removed"
Bar 4  6-8s    THE DROP. Cursor clicks "Drop it in the box". The button folds back into the note, which drops
               into the box slot. The padlock shackle snaps shut on beat 3. Big type: "Locked on your phone"
Bar 5  8-10s   The sealed note becomes the text the server stores: real-looking base64 ciphertext
               (generate it with the app's own encryption) scrolls past. Big type: "We can't read it either"
Bar 6  10-12s  Owner side. The padlock opens (passphrase dots fill on beats 1-2). Inbox rows unscramble
               letter by letter, left to right, on beats 3-4. Key word: "Only the CO"
Bar 7  12-14s  PAYOFF, the biggest beat. Message detail with the photo. On the downbeat the status flips to
               "Resolved" and the camera pushes in. Big type: "Heard"
Bar 8  14-16s  The note/padlock morphs into the logo (static/icons/icon.svg). End card: name + promise +
               link line. Final half-beat: fade to black
</structure>

<build>
1. One HTML file at 1920x1080 in promo/ (not in the Django app). Every style is computed from time inside
   window.seek(t): no CSS animations, no timers, no state carried between frames. seek() returns a Promise that
   resolves after fonts and every image needed for that frame have decoded.
2. Springs and exponential easing are pure functions of time. Motion blur follows speed and direction on
   fast moves (directional blur on the moving layer, never on text that should be read).
3. Soundtrack:
   a. Default: compose in code with OfflineAudioContext at 120 BPM: soft kick on every beat, a low pad, a
      "paper slide" swoosh for the note, a short click for UI clicks, a solid "lock" hit on the bar-4 snap and a
      bigger hit on bar 7. Render to WAV.
   b. If I give a track: analyse with numpy/librosa (tempo, beat grid, energy per bar, the drop). Snap the grid to
      the real kick hits. Put the bar-7 payoff on the drop.
   c. Place each sound effect so its measured PEAK (not its file start) lands on the event. Keep effects
      quiet under the music. Loudnorm the final mix to -14 LUFS, true peak -1 dBTP.
4. Render with Playwright at 60 fps: 3 subframes per frame (t - 1/240 s, t, t + 1/240 s), blend with ffmpeg
   tmix for real motion blur, encode H.264 (yuv420p, CRF 18, -preset veryfast), mux the audio. If real clips are
   used: extract to 30 fps JPEG sequences with ffmpeg and swap img sources per frame.
5. Before the full render: render one frame per beat (32 frames) plus every scene boundary and LOOK at them.
   Fix anything cluttered, overlapping, off the beat, hard to read, or not matching the real UI.
6. Deliver: promo/out/suggestion-box-promo.mp4 (16:9). Also a vertical 1080x1920 cut (reframe; don't squash)
   and promo/out/hero-loop.webm: bars 4-6 only, muted, 6 s, seamless loop, under 1.5 MB.
</build>

<gotchas>
- Never set opacity or filter on a preserve-3d element (it flattens and both faces show). Fade its wrapper.
- Measure element positions at runtime for match cuts. Never hard-code them.
- When a shape fills the frame, scale it past all four corners.
- Give outgoing and incoming text separate timing so letters never overlap.
- Never put will-change on anything the camera scales, or text renders blurry.
- Only use music and sound effects whose licence allows commercial use. Write the licence in promo/CREDITS.md.
- No real people, names, unit names, insignia or phone numbers. Seed data only.
</gotchas>

<start>
1. Show me what you found: the real UI pieces you'll rebuild, colours, sizes, copy.
2. Show the through-line object and how it changes in each scene.
3. Show the final beat-by-beat storyboard (times in seconds and beats).
Then build exactly that without asking me anything else. Give me the final MP4, the vertical cut and the hero loop.
</start>
```

---

## Optional: put the loop on the intro page
When `hero-loop.webm` exists, copy it to `static/video/hero-loop.webm` and ask Claude Code to:
> Show static/video/hero-loop.webm in the intro hero instead of the SVG on screens wider than 768px. Use `<video autoplay muted loop playsinline>` with the SVG as the fallback. Respect prefers-reduced-motion (show the SVG). The CSP already allows `media-src 'self'`.
