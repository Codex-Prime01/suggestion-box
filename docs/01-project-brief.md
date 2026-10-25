# Project brief — Suggestion Box

_What the client asked for, in plain words. Taken from his WhatsApp voice notes (23 Oct 2026)._

## The idea
A website that works like a **physical suggestion box** for soldiers.

- A soldier opens the link, fills in **name, rank, unit** and their complaint or suggestion, then sends it.
- Once sent, it's **gone** for them. They can't see it again, edit it, or delete it.
- **Only the oga (the box owner — a senior officer) can open the box** and read messages, with the sender's details.
- Nobody else can see the messages. Especially **not the middle commanders**. If a soldier complains about his commander, that commander must never find out.

> "Once you drop it, bam, it drops. No room for editing. No room for checking again. Just like a suggestion box — only the owner goes and picks it."

## How it's different from NGL / Secret Message
| | NGL-style apps | This project |
|---|---|---|
| Sender identity | Hidden from everyone | **Visible to the owner only** |
| Who owns a box | Anyone can sign up | **One owner** (the oga) |
| Purpose | Fun / social | Complaints, welfare, feedback in a unit |
| Biggest risk | Bullying | **Retaliation** if the wrong person reads it |

## Client wishes
- Build the **backend first**. The design can change later.
- The oga doesn't know about it yet. The client will pitch it to him, so we need a **demo** first.
- The background/design must be **changeable** later, depending on what the oga wants.

## Client's answers (voice notes, 24 Oct 2026)
- **Personalise it to the oga.** It's his own box (name can change later).
- **Name, rank, army number: optional.** Soldiers decide what to reveal. **Unit is a must**, so the oga knows where to investigate.
- **Keep civilians out:** some check that the sender is really army.
- **Photos as evidence:** yes.
- **Replies:** no accounts where people can go back and see messages. If a soldier wants contact, they drop their phone number.
- **Backup key:** yes, so messages are never just lost.
- Everything can still be edited to the oga's taste after he sees it.

## Status
- [x] Requirements gathered from voice notes
- [x] Client answered the first round of questions (24 Oct)
- [x] Phase 1 demo built and tested locally
- [x] Phase 2 built: encryption, backup key, photos, new fields
- [x] Phase 3 built: intro page, 2-step form, 2FA, lockout, alerts, no CDNs (access code dropped)
- [ ] A few questions still open → see `02-decisions.md`
