/*
  Oga side. Unlocks the private key in this tab, then opens messages,
  photos and notes right here in the browser.
*/
(function () {
  "use strict";

  const keyEl = document.getElementById("box-key");
  const KEY = keyEl ? JSON.parse(keyEl.textContent) : {};
  const page = document.body.dataset.page || "";
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function showError(el, msg) { el.textContent = msg; el.hidden = false; }
  function busy(btn, on, label) {
    if (on) { btn.dataset.label = btn.textContent; btn.textContent = label; btn.disabled = true; }
    else { btn.textContent = btn.dataset.label || btn.textContent; btn.disabled = false; }
  }

  // Wipe the unlocked key when logging out.
  $$("form[data-logout]").forEach((f) => f.addEventListener("submit", () => SB.forgetKey()));

  // Pages that need the unlocked key: send to the unlock page if it's missing.
  async function requireKey() {
    const sk = await SB.recalledKey(KEY.public_key);
    if (!sk) {
      const next = encodeURIComponent(location.pathname + location.search);
      location.replace(document.body.dataset.unlockUrl + "?next=" + next);
      return null;
    }
    return sk;
  }

  async function openPayload(sk, b64) {
    try { return JSON.parse(await SB.openText(KEY.public_key, sk, b64)); }
    catch (e) { return null; }
  }

  // ---------- key setup (first time) ----------
  async function pageKeySetup() {
    const step1 = $("#step-passphrase"), step2 = $("#step-backup");
    const err = $("#setup-error");
    let pending = null;

    $("#make-key").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      err.hidden = true;
      const p1 = $("#pass1").value, p2 = $("#pass2").value;
      if (p1.length < 10) return showError(err, "Use at least 10 characters. A short sentence works well.");
      if (p1 !== p2) return showError(err, "The two passphrases don't match.");
      busy(btn, true, "Making your key…");
      try {
        const kp = await SB.newKeyPair();
        const locked = await SB.lockPrivateKey(kp.sk, p1);
        pending = { sk: kp.sk, pk: kp.pk, locked };
        $("#backup-code").textContent = await SB.toBackupCode(kp.sk);
        step1.hidden = true; step2.hidden = false;
      } catch (ex) { showError(err, ex.message); }
      busy(btn, false);
    });

    $("#download-backup").addEventListener("click", () => {
      SB.downloadText("suggestion-box-BACKUP-KEY.txt",
        "SUGGESTION BOX — BACKUP KEY\n\nKeep this somewhere safe and private (print it, lock it away).\n" +
        "Anyone with this key can read every message. If you lose BOTH this and your passphrase,\n" +
        "the messages can never be opened again.\n\n" + $("#backup-code").textContent + "\n");
    });

    $("#confirm-saved").addEventListener("change", (e) => { $("#finish-setup").disabled = !e.target.checked; });

    $("#finish-setup").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      const err2 = $("#setup-error-2");
      busy(btn, true, "Saving…");
      try {
        const res = await SB.postJSON(location.pathname, { public_key: pending.pk, ...pending.locked });
        await SB.rememberKey(pending.sk, pending.pk);
        location.replace(res.redirect);
      } catch (ex) { showError(err2, ex.message); busy(btn, false); }
    });
  }

  // ---------- unlock ----------
  async function pageUnlock() {
    const next = document.body.dataset.next || "/";
    const err = $("#unlock-error");

    $("#unlock-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      err.hidden = true;
      const btn = $("button", e.currentTarget);
      busy(btn, true, "Unlocking…");
      try {
        const sk = await SB.unlockPrivateKey(KEY.encrypted_private_key, KEY.salt, $("#passphrase").value);
        await SB.rememberKey(sk, KEY.public_key);
        location.replace(next);
      } catch (ex) { showError(err, ex.message); busy(btn, false); }
    });

    $("#recover-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const err2 = $("#recover-error");
      err2.hidden = true;
      const btn = $("button", e.currentTarget);
      const p1 = $("#new-pass1").value, p2 = $("#new-pass2").value;
      if (p1.length < 10) return showError(err2, "New passphrase: use at least 10 characters.");
      if (p1 !== p2) return showError(err2, "The two new passphrases don't match.");
      busy(btn, true, "Checking backup key…");
      try {
        const sk = await SB.fromBackupCode($("#backup-input").value);
        if ((await SB.publicKeyFor(sk)) !== KEY.public_key) throw new Error("That backup key doesn't belong to this box.");
        const locked = await SB.lockPrivateKey(sk, p1);
        await SB.postJSON(document.body.dataset.rewrapUrl, { public_key: KEY.public_key, ...locked });
        await SB.rememberKey(sk, KEY.public_key);
        location.replace(next);
      } catch (ex) { showError(err2, ex.message); busy(btn, false); }
    });
  }

  // ---------- inbox ----------
  async function pageInbox() {
    const sk = await requireKey();
    if (!sk) return;
    const rows = $$("[data-payload]");
    await Promise.all(rows.map(async (row) => {
      const p = await openPayload(sk, row.dataset.payload);
      if (!p) { $(".js-who", row).textContent = "⚠ Can't open this message"; return; }
      $(".js-who", row).textContent = [p.rank, p.name].filter(Boolean).join(" ") || "(no name)";
      $(".js-unit", row).textContent = p.unit || "no unit";
      $(".js-preview", row).textContent = p.body;
      row.dataset.search = [p.name, p.rank, p.unit, p.service_number, p.phone, p.body].join(" ").toLowerCase();
    }));

    // Search runs here in the browser, because the server can't read messages.
    const search = $("#search");
    const empty = $("#no-match");
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      let shown = 0;
      rows.forEach((r) => {
        const hit = !q || (r.dataset.search || "").includes(q);
        r.hidden = !hit; if (hit) shown++;
      });
      empty.hidden = shown !== 0 || rows.length === 0;
    });
  }

  // ---------- one message ----------
  async function pageDetail() {
    const sk = await requireKey();
    if (!sk) return;
    const art = $("#message");
    const p = await openPayload(sk, art.dataset.payload);
    if (!p) { $("#body").textContent = "⚠ This message can't be opened with your key."; return; }
    for (const f of ["name", "rank", "service_number", "unit", "phone"]) {
      $("#f-" + f).textContent = p[f] || "—";
    }
    if (p.phone) {
      const a = document.createElement("a");
      a.href = "tel:" + p.phone.replace(/[^0-9+]/g, "");
      a.textContent = p.phone; a.className = "underline";
      $("#f-phone").replaceChildren(a);
    }
    $("#body").textContent = p.body;

    // Photos: download the locked bytes, open them here, show them.
    for (const holder of $$("[data-attachment-url]")) {
      try {
        const r = await fetch(holder.dataset.attachmentUrl, { credentials: "same-origin" });
        const bytes = await SB.openBytes(KEY.public_key, sk, new Uint8Array(await r.arrayBuffer()));
        const url = URL.createObjectURL(new Blob([bytes], { type: "image/jpeg" }));
        const img = document.createElement("img");
        img.src = url; img.alt = "Attached photo"; img.className = "w-full rounded-lg";
        const link = document.createElement("a");
        link.href = url; link.target = "_blank"; link.rel = "noopener"; link.appendChild(img);
        holder.replaceChildren(link);
      } catch (e) {
        holder.textContent = "⚠ Couldn't open this photo.";
      }
    }

    // Private notes: open the old note, lock the new one before saving.
    const noteForm = $("#note-form");
    const noteBox = $("#note-text");
    const hidden = $("input[name=owner_note]", noteForm);
    if (hidden.value) {
      try { noteBox.value = await SB.openText(KEY.public_key, sk, hidden.value); }
      catch (e) { noteBox.value = ""; }
    }
    noteForm.addEventListener("submit", async (e) => {
      if (noteForm.dataset.sealed) return;
      e.preventDefault();
      hidden.value = noteBox.value.trim() ? await SB.sealText(KEY.public_key, noteBox.value) : "";
      noteForm.dataset.sealed = "1";
      noteForm.submit();
    });

    $("#delete-form").addEventListener("submit", (e) => {
      if (!confirm("Delete this message forever? This cannot be undone.")) e.preventDefault();
    });
  }

  // ---------- change passphrase / show backup key ----------
  async function pageKeyManage() {
    const sk = await requireKey();
    if (!sk) return;

    $("#show-backup").addEventListener("click", async () => {
      $("#backup-code").textContent = await SB.toBackupCode(sk);
      $("#backup-wrap").hidden = false;
    });
    $("#download-backup").addEventListener("click", async () => {
      SB.downloadText("suggestion-box-BACKUP-KEY.txt",
        "SUGGESTION BOX — BACKUP KEY\n\nKeep this safe and private.\n\n" + (await SB.toBackupCode(sk)) + "\n");
    });

    $("#change-pass-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = $("#change-error"), ok = $("#change-ok");
      err.hidden = true; ok.hidden = true;
      const btn = $("button", e.currentTarget);
      const p1 = $("#cp1").value, p2 = $("#cp2").value;
      if (p1.length < 10) return showError(err, "Use at least 10 characters.");
      if (p1 !== p2) return showError(err, "The two passphrases don't match.");
      busy(btn, true, "Saving…");
      try {
        const locked = await SB.lockPrivateKey(sk, p1);
        await SB.postJSON(document.body.dataset.rewrapUrl, { public_key: KEY.public_key, ...locked });
        ok.hidden = false; e.currentTarget.reset();
      } catch (ex) { showError(err, ex.message); }
      busy(btn, false);
    });
  }

  const pages = {
    "key-setup": pageKeySetup, unlock: pageUnlock, inbox: pageInbox,
    detail: pageDetail, "key-manage": pageKeyManage,
  };
  if (pages[page]) pages[page]();
})();
