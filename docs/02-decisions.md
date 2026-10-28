# Decisions log

Write every decision here, with the date. When the client answers, move a question from "Open" to "Decided".

## Decided
| Date | Decision | Why |
|---|---|---|
| 2026-10-23 | **Django + PostgreSQL + Django templates + Tailwind** | Perey already ships Django. Login, forms and security come built in. |
| 2026-10-23 | **No sender accounts. No "my messages" page.** | Once dropped, the sender can't see it again. |
| 2026-10-23 | **Exactly one owner account** can open owner pages. Even the Django superuser gets 403. | Only the oga opens the box. |
| 2026-10-23 | **Messages are NOT in the Django admin.** | Same reason. |
| 2026-10-23 | **Design lives in the database** (theme, title, background URL). | The look changes later without code changes. |
| 2026-10-23 | **The app must run on any host.** | We may leave Render. See `05-deployment-options.md`. |
| 2026-10-23 | **The IP is never saved** with a message. It's only kept in memory for 1 hour, for rate limiting. | Less data held = less to leak. |
| 2026-10-24 | **One owner.** `owner_display_name` is optional and **left blank for now**; the site then says "the commanding officer". | Client: personalise later. |
| 2026-10-24 | **Name, rank, army number: optional. Unit: required.** | Client: soldiers decide what to reveal, but the oga must know which unit to investigate. |
| 2026-10-24 | **Optional phone number for replies.** No accounts, no reply inbox. | Client + Perey: "if they want contact, they drop their number." |
| 2026-10-28 | **CO shown as rank + name only** (`owner_rank` + `owner_name`, replaces `owner_display_name`). No appointment. Number field labelled **SvcNo/ArmyNo** (officers use service number, other ranks army number). | Client voice note: the box is personal to him. |
| 2026-10-28 | **Clear inbox button.** Deletes the current filter, or everything if no filter. Oga must type DELETE. | Perey. |
| 2026-10-24 | **Up to 3 photos per message** as evidence. Shrunk to 1600px, re-saved as JPG in the browser (removes GPS/phone info), then encrypted. Stored in the database. | Client wants photo evidence. The database works on any host (no file storage needed). |
| 2026-10-24 | **End-to-end encryption** (libsodium sealed boxes). Everything the sender types + photos + the oga's notes are encrypted. Only `category`, `status` and dates stay plain. | So "only the oga can read it" is actually true: not the host, not the developer. |
| 2026-10-24 | **Backup key** shown once at setup (64 characters, downloadable). Can be shown again from the Key page while unlocked. Recovery = backup key + new passphrase. | Client: "you have to have a backup key." |
| 2026-10-24 | libsodium is **bundled in `static/vendor/`**, not loaded from a CDN. | The code that handles the keys shouldn't come from someone else's server. |

| 2026-10-24 (eve) | **No unit access code.** Removed. | Client's call. Spam is handled by the rate limit + honeypot. |
| 2026-10-24 (eve) | **No army-number format check.** | Client's call. The field stays optional and free text. |
| 2026-10-24 (eve) | **No approval from above needed.** | Client confirmed. |
| 2026-10-24 (eve) | **Data doesn't have to stay in Nigeria.** Any host is fine. | Client confirmed. |
| 2026-10-24 (eve) | **2-step drop form:** "About you" first, then "Your message". | Client: keep the page compact and friendly. |
| 2026-10-24 (eve) | **Intro page at `/`.** Form moved to `/drop/`. | Client wants a short animated page that explains the site. |
| 2026-10-24 (eve) | **Phase 3 security built:** 2-step login (TOTP + backup codes), login lockout, shared-cache rate limit, content-free alerts, self-hosted CSS/fonts, strict CSP, PWA manifest. | Before real soldiers use it. |

## Open
1. The oga's name/rank, crest/logo, colours, background (all settings, no code needed).
2. The live link (for the end card of the promo video and the share link).
