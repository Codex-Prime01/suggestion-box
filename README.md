# Suggestion Box 🔒

A digital suggestion box for a military unit. Soldiers drop complaints and suggestions (with photos if they want). **Only the commanding officer can read them.** Messages are encrypted on the soldier's phone before they're sent, so not even the server or the developer can read them. Once sent, the soldier can't see, edit or delete the message.

## Run it on your computer (Windows)

```powershell
cd suggestion-box
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createcachetable
python manage.py setup_owner oga        # asks for the oga's LOGIN password
python manage.py runserver
```

### First-time setup (in the browser)
1. **http://127.0.0.1:8000/oga/**: log in as `oga`.
2. **Set up 2-step login**: scan the QR code with an authenticator app, then save the 8 backup codes.
3. **Make your key**: choose a passphrase, then save the backup key.
4. **http://127.0.0.1:8000/** is the intro page. Click "Drop a message" and send a test from a private window.
5. Back in the inbox, your message appears, unlocked only in your tab.

Fake demo messages (after step 3): `python manage.py seed_demo`

> Coming from an older version? Delete `db.sqlite3` first.

**Continuing in Claude Code?** Open `CONTINUE.md`.

## Run the tests
```powershell
python manage.py test box
```

## Docs
Everything else is in [`docs/`](docs/).
