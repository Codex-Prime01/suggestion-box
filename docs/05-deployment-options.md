# Deployment options (moving off Render)

> ⚠️ Prices and free tiers change all the time. When we're ready to deploy, **check these again**. This is the shortlist, not the final answer.

The app is built to run **anywhere**: all settings come from env vars, and it only needs Python, Postgres and `gunicorn config.wsgi`. Switching hosts = set env vars + point the domain.

## Shortlist
| Option | Type | Good for | Watch out for |
|---|---|---|---|
| **Railway** | PaaS (like Render) | Easiest move from Render. Postgres with one click | Usage-based billing. Set a spending limit |
| **Fly.io** | PaaS (containers) | Cheap small apps, servers near users | Needs a Dockerfile, a bit more setup |
| **Koyeb** | PaaS | Simple Git deploys | Small free tier, check the limits |
| **PythonAnywhere** | Python hosting | Super simple for Django, beginner friendly | Free tier is limited. Paid needed for a custom domain |
| **A small VPS** (Hetzner, DigitalOcean, Contabo, Vultr) | Your own Linux server | **No surprise limits.** Full control, cheap monthly price | You manage updates, firewall and backups yourself |
| **Oracle Cloud "Always Free" VM** | Free VPS | Free forever if you get in | Sign-up can be picky about cards. You manage everything |

## Separate database (so the app host doesn't matter)
| Option | Notes |
|---|---|
| **Neon** | Serverless Postgres with a free tier |
| **Supabase** | Postgres + extras with a free tier. Free projects pause when idle |

## Recommendation (for now)
- **Demo:** Railway or Koyeb, or keep Render just for the demo. It's only for showing the oga.
- **Real thing:** a **small VPS**. No sleeping apps, no database expiring, a fixed price, and **you know where the data lives**. That matters for military data. (We can write a setup script so it's not scary.)
- ✅ Client confirmed: the data does **not** have to stay in Nigeria. Any host works.

## Checklist for any host
- [ ] `DEBUG=False`
- [ ] Strong random `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` set to the real domain
- [ ] `DATABASE_URL` pointing to Postgres
- [ ] Change `OWNER_URL_PREFIX` and `ADMIN_URL_PREFIX` from the defaults
- [ ] Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py createcachetable`
- [ ] Node is NOT needed on the server (`static/css/app.css` is committed)
- [ ] Start command: `gunicorn config.wsgi --bind 0.0.0.0:$PORT`
- [ ] Run `python manage.py setup_owner <username>` once (in the host's shell)
- [ ] **Do NOT** run `seed_demo` on the real box
- [ ] Backups switched on
- [ ] Alerts: `ALERT_EMAIL` + SMTP, or Telegram vars
- [ ] If behind a proxy/CDN, check `X-Forwarded-For` is set (used by the rate limit + lockout)
