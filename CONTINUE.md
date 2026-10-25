# CONTINUE.md — pick up here in Claude Code

_Last updated: 24 Oct 2026. Phases 1–3 are built and tested. Next: run it on your machine, then deploy._

## 1. Open it in Claude Code
```powershell
cd path\to\suggestion-box
git init; git add -A; git commit -m "Suggestion Box: phases 1-3"
claude
```
Then paste this as your first message:

> Read CONTINUE.md, CLAUDE.md and everything in docs/. Then run the tests (`python manage.py test box`) and tell me in 5 lines where the project stands and what you'd do next. Don't change anything yet.

`CLAUDE.md` holds the golden rules. Claude Code reads it automatically every session.

## 2. Run it locally (Windows)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createcachetable
python manage.py setup_owner oga          # the oga's LOGIN password
python manage.py runserver
```
**Delete any old `db.sqlite3` first.** The database layout changed since the phase 1 demo.

Then, in the browser:
1. **http://127.0.0.1:8000/** is the intro page (what soldiers see first). "Drop a message" goes to `/drop/`.
2. **http://127.0.0.1:8000/oga/** is the oga's side. Log in, then:
   - **2-step login setup**: scan the QR with Google/Microsoft Authenticator, type the code, write down the 8 backup codes
   - **Make your key**: passphrase, then save the backup key (download it)
   - **Settings**: title, theme, optional name. The box is open.
3. Send a test from a private window, then read it in the inbox.
4. Fake data for demos (after the key exists): `python manage.py seed_demo`

## 3. What's built
| Area | Status |
|---|---|
| Intro page (animated: note drops into box, padlock locks; scroll reveals; reduced-motion safe) | ✅ |
| 2-step drop form: **About you** (unit required, rest optional, phone for reply) → **Message** (type chips, text, up to 3 photos) | ✅ |
| End-to-end encryption in the browser (libsodium sealed boxes): text, photos, owner notes | ✅ |
| Photo shrinking + removal of GPS and other hidden data before encryption | ✅ |
| Owner key: passphrase lock, backup key, recovery, change passphrase | ✅ |
| Owner 2-step login (authenticator app + 8 one-time backup codes) | ✅ |
| Login lockout after 5 wrong passwords (django-axes, 1 hour) | ✅ |
| Spam limit (5/hour/IP) in a shared cache (DB table or Redis) + honeypot | ✅ |
| "New message" alerts by email/Telegram, never with content, 10-min cooldown | ✅ (needs env vars) |
| Tailwind compiled to `static/css/app.css`, fonts bundled, no CDNs, strict CSP | ✅ |
| PWA manifest + icons ("Add to home screen") | ✅ |
| Tests: 34 Python tests + a full browser run (2FA, key, 2-step form, photo, decrypt, backup code, lockout) | ✅ |

**Removed on the client's request:** unit access code, army-number validation. No approval needed. The data doesn't have to stay in Nigeria. The oga's name is blank for now, so the site says "the commanding officer".

## 4. Next steps (in order)
1. **Run it locally and click through everything** (section 2).
2. **Deploy.** Ask Claude Code: _"Read docs/05-deployment-options.md, check current prices, recommend one, and walk me through deploying."_ Build steps are in that doc.
3. **Turn on alerts.** Set `ALERT_EMAIL` + SMTP, or `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (see `.env.example`).
4. **Backups.** Turn on the host's daily Postgres backups. Messages are encrypted, so backups are safe to store, but they're useless without the oga's key.
5. **Show the oga** and collect his design wishes: name, crest, colours, background. These are all settings, not code.
6. **Promo video.** `docs/prompts/intro-promo-video.md` has the merged prompt. Paste it into Claude Code.
7. Maybe later: captcha (only if spam appears), several boxes (one per commander), monthly summary.

## 5. Handy commands
```powershell
python manage.py test box                         # run all tests
npm install; npm run css                          # rebuild Tailwind after changing classes (needs Node)
python manage.py setup_owner oga --reset-2fa --keep-password   # oga lost phone AND backup codes
python manage.py axes_reset                       # clear login lockouts
python manage.py dumpdata box --output backup.json # manual backup (stays encrypted)
```

## 6. If something breaks
- **Inbox says "Can't open this message":** the key changed. Never replace the key pair, only re-wrap it (see CLAUDE.md rule 9).
- **Blank styles:** `static/css/app.css` is missing. Run `npm run css`, then `collectstatic` on the server.
- **"Too many tries":** `python manage.py axes_reset`.
- **2FA code rejected:** the phone's clock must be set to automatic time.
