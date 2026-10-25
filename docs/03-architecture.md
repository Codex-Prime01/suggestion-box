# Architecture

## Stack
| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Framework | Django 5.2 (LTS) |
| Database | SQLite on your laptop → PostgreSQL in production (`DATABASE_URL`) |
| Encryption | libsodium in the browser (`static/vendor/`), PyNaCl in Python (tests + demo seeding) |
| Frontend | Django templates + Tailwind v4 (compiled to `static/css/app.css`) + plain JS. Fonts bundled (Saira) |
| Owner login | Password + 2-step login (django-otp TOTP + 8 backup codes) + lockout (django-axes) |
| Cache | DB table (`createcachetable`) or Redis (`REDIS_URL`), shared by all server processes |
| Static files | WhiteNoise |
| App server | Gunicorn |

## Folder map
```
suggestion-box/
├── CLAUDE.md                ← rules for Claude Code / any dev
├── README.md                ← how to run it
├── docs/
├── config/                  ← settings + main urls
├── box/
│   ├── models.py            ← BoxSettings (1 row), Message, Attachment
│   ├── forms.py             ← checks shape/size of encrypted data
│   ├── views.py             ← sender + owner views, key endpoints
│   ├── middleware.py        ← Content-Security-Policy etc.
│   ├── context_processors.py← gives the locked key ONLY to owner pages
│   ├── alerts.py            ← 'new message' email/Telegram (no content)
│   ├── tests.py             ← 34 tests
│   └── management/commands/ ← setup_owner, seed_demo
├── templates/
└── static/
    ├── css/themes.css       ← themes + field styles
    ├── js/sb-crypto.js      ← all the encryption helpers
    ├── js/drop.js           ← sender: lock message + photos, send
    ├── js/owner.js          ← oga: key setup, unlock, recover, read, notes
    └── vendor/              ← libsodium (don't edit)
```

## How the encryption works (plain English)
Think of a **padlock and key**.

1. **Key setup (once).** The oga's browser makes a padlock (public key) and its key (private key).
   - The **padlock** is saved on the server. Anyone can use it to lock things.
   - The **key** is locked inside a little safe that opens with the oga's **passphrase**, then saved on the server. The server can't open that safe.
   - The oga gets a **backup key**: the raw private key written as 64 characters. He prints it or keeps it somewhere locked.
2. **A soldier sends a message.** Their browser snaps the padlock shut on everything they typed and their photos, then sends the locked box. Once locked, even the soldier can't open it.
3. **The oga reads.** He logs in, types his passphrase, and his browser opens the safe to get the key. The key is kept in this browser tab only (`sessionStorage`) and is wiped when he closes the tab or logs out. His browser unlocks messages and photos.
4. **Forgot passphrase?** He types the backup key plus a new passphrase. The browser checks the backup key matches the padlock, then re-locks it with the new passphrase. Old messages still open.
5. **Lost both?** Messages can never be opened again. That's the price of real privacy.

Technical names: `crypto_box_seal` (X25519 + XSalsa20-Poly1305) for messages/photos/notes. The private key is wrapped with `crypto_secretbox` using a key from `crypto_pwhash` (Argon2id, interactive limits).

## What the server can and can't see
| Can see | Can't see |
|---|---|
| A message arrived, when, its type (complaint/welfare…) | Name, rank, army number, unit, phone |
| Its status (new/read/resolved) | The message text |
| How many photos, their size | The photos |
| | The oga's notes |
| | The oga's private key (it's locked) |

## Data model
**BoxSettings** (1 row): `owner`, `owner_display_name`, `title`, `subtitle`, `theme`, `background_image_url`, `is_open`, `public_key`, `encrypted_private_key`, `key_salt`, `key_created_at`

**Message**: `id` (UUID), `category`, `created_at`, `status`, `read_at`, `payload` (encrypted JSON: `{v, name, rank, service_number, unit, phone, body}`), `owner_note` (encrypted)

**Attachment**: `id` (UUID), `message`, `data` (encrypted JPG bytes), `size`, `created_at`

## Pages
| URL | Who | What |
|---|---|---|
| `/` | Anyone | Animated intro page |
| `/drop/` | Anyone | 2-step form: About you → Message |
| `/<OWNER>/2fa/setup/`, `/<OWNER>/2fa/` | Oga | Link authenticator app / type the code |
| `/sent/` | Anyone | "Delivered". No content shown |
| `/<OWNER>/login/` | Oga | Login |
| `/<OWNER>/key/setup/` | Oga, first time | Make key + get backup key |
| `/<OWNER>/key/unlock/` | Oga | Type passphrase, or recover with backup key |
| `/<OWNER>/key/manage/` | Oga | Change passphrase, show/download backup key |
| `/<OWNER>/` | Oga | Inbox (search runs in the browser) |
| `/<OWNER>/m/<uuid>/` | Oga | Read message + photos, encrypted notes, status, delete |
| `/<OWNER>/settings/` | Oga | Name, look, open/close, alert status |

## Security checklist (done)
- Only the owner account can open owner pages (403 for everyone else, superusers too)
- End-to-end encryption for content, photos and notes
- Photos stripped of hidden data (GPS etc.) before encryption
- 2-step login for the oga + lockout after 5 wrong passwords
- Content-free 'new message' alerts with a cooldown
- Honeypot + rate limit (per IP, in memory only)
- Content-Security-Policy: everything from this site only (no CDNs), no `eval`, no inline scripts
- Owner pages `no-store`, 30-min idle logout, unlocked key wiped on logout/tab close
- Secure cookies, HTTPS redirect, HSTS when `DEBUG=False`
- `noindex`

## Known limits (be honest with the client)
- **Names are claimed, not checked.** Anyone with the link can send, and anyone can type any name. The oga should treat names as "claimed".
- If someone gets into the oga's **unlocked** browser tab (e.g. his phone left open), they can read messages. Close the tab, lock your phone.
- If the server itself were hacked and the JS changed, future messages could be captured. Hosting security still matters.
