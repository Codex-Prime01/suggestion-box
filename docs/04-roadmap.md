# Roadmap

## Phase 1 — Demo ✅ (tested locally by Perey, 24 Oct)
- [x] Drop page, "sent" page, closed page
- [x] Owner login, inbox, message detail, notes, status, delete
- [x] Owner settings + 4 themes
- [x] Honeypot + rate limit

## Phase 2 — Client's answers + make it safe ✅ (24 Oct)
- [x] Personalised to the oga (`owner_display_name`)
- [x] Unit required; name/rank/army number optional; optional phone for replies
- [x] ~~Unit access code gate~~ (removed in phase 3 at the client's request)
- [x] Up to 3 photos, resized + location data removed, encrypted
- [x] End-to-end encryption with passphrase + backup key + recovery
- [x] Encrypted owner notes
- [x] Content-Security-Policy
- [x] 28 Python tests + full browser end-to-end check

## Phase 3 — Safe for real use ✅ (24 Oct, evening)
- [x] Client changes: no access code, blank oga name, 2-step drop form
- [x] Animated intro page (`/`), form at `/drop/`
- [x] 2-step login for the oga (authenticator app + backup codes)
- [x] Login lockout (`django-axes`)
- [x] Shared cache for the rate limit (DB table / Redis)
- [x] "New message" alerts (email/Telegram), no content, cooldown
- [x] Tailwind compiled, fonts self-hosted, CSP tightened to 'self'
- [x] Favicon + PWA manifest
- [x] 34 tests + full browser run
- [ ] Captcha: skipped on purpose; add only if spam shows up

## Phase 4 — Launch
- [ ] Hosting (see `05-deployment-options.md`), domain, HTTPS
- [ ] Daily database backups on the host
- [ ] Alerts env vars set
- [ ] Promo video (`docs/prompts/intro-promo-video.md`)
- [ ] Short "how to use" note for soldiers
- [ ] Handover sheet for the oga: login password vs key passphrase, authenticator app, backup codes, backup key

## Maybe later
- Multiple boxes (one per commander)
- Monthly summary: messages per category/status
