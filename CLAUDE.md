# CLAUDE.md — Suggestion Box

Start with `CONTINUE.md` (where things stand), then `docs/`. `01-project-brief.md` explains what we're building. `02-decisions.md` lists what's decided and what's still open. `03-architecture.md` explains the encryption.

## What this is
A confidential suggestion/complaint box for soldiers, personalised to one oga (commanding officer). `/` is an animated intro page. `/drop/` is a 2-step form: About you (unit required; name, rank, army number, phone optional), then Message (type, text, up to 3 photos). Everything is **encrypted in the sender's browser** with the oga's public key. Only the oga can read it.

## Golden rules (don't break these)
1. **Never** add a way for senders to see their sent messages.
2. **Never** register `Message`/`Attachment` in the Django admin.
3. Every owner view uses `@owner_required` (owner + key, plus 2-step login when `OWNER_2FA=True`; off by default at the client's request). Non-owners get 403, superusers included. Only the 2FA pages use `@owner_only`.
4. **Never** send plain message content to the server. New sender fields go inside the encrypted `payload` JSON (bump `v` if the shape changes).
5. **Never** log or email message content. Notifications say "new message", nothing more.
6. **Never** store the sender's IP with a message.
7. The locked private key (`key_data`) is only sent to the owner's own pages (`context_processors.py`).
8. Everything is self-hosted. Don't add CDNs. Keep the CSP in `box/middleware.py` at 'self', with no `unsafe-eval` and no inline `<script>`; JS goes in `static/js/`.
   After changing Tailwind classes, run `npm run css` and commit `static/css/app.css`.
9. Changing the key pair makes every old message unreadable. Only `key_rewrap` (same public key) is allowed.
10. All config comes from env vars. No host-specific code.
11. Run the tests after every change: `python manage.py test box`. Add a test for every new rule.

## Commands
```bash
python manage.py runserver
python manage.py test box
python manage.py makemigrations box && python manage.py migrate
python manage.py createcachetable          # once, after migrate
python manage.py setup_owner <username>   # make/reset the oga's login (--reset-2fa --keep-password if he lost his phone)
python manage.py axes_reset               # clear login lockouts
npm run css                               # rebuild Tailwind
python manage.py seed_demo                # fake encrypted messages (after key setup), demo only
```

## Style
- Plain, simple English in UI copy and docs.
- Tailwind classes in templates. Theme colours are CSS variables in `static/css/themes.css`.
- One app (`box`), function-based views, plain JS (no framework).

## Next up
`CONTINUE.md`, section 4.
