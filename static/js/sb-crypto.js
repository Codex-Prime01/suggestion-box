/*
  Suggestion Box — shared encryption helpers (runs in the browser).

  How it works, in plain words:
  - The oga has a KEY PAIR: a public key (a padlock anyone can snap shut)
    and a private key (the only key that opens it).
  - Senders' browsers lock each message with the public key ("sealed box").
    After that, not even the sender can open it again.
  - The private key never leaves the oga's browser unlocked. On the server
    it's stored locked with his passphrase (Argon2id + secretbox).
  - The BACKUP KEY is just the private key written as 64 hex characters.
    Whoever has it can read every message, so it must be kept safe.

  Uses libsodium (static/vendor), loaded before this file.
*/
(function () {
  "use strict";

  let readyPromise = null;
  function sodium() {
    if (!readyPromise) readyPromise = window.sodium.ready.then(() => window.sodium);
    return readyPromise;
  }

  const SK_STORE = "sb.sk";      // unlocked private key, this browser tab only
  const PK_STORE = "sb.pk";

  function b64(s, u8) { return s.to_base64(u8, s.base64_variants.ORIGINAL); }
  function unb64(s, str) { return s.from_base64(str, s.base64_variants.ORIGINAL); }

  // ---- passphrase lock for the private key ----
  async function lockPrivateKey(sk, passphrase) {
    const s = await sodium();
    const salt = s.randombytes_buf(s.crypto_pwhash_SALTBYTES);
    const key = s.crypto_pwhash(32, passphrase, salt,
      s.crypto_pwhash_OPSLIMIT_INTERACTIVE, s.crypto_pwhash_MEMLIMIT_INTERACTIVE,
      s.crypto_pwhash_ALG_ARGON2ID13);
    const nonce = s.randombytes_buf(s.crypto_secretbox_NONCEBYTES);
    const ct = s.crypto_secretbox_easy(sk, nonce, key);
    const blob = new Uint8Array(nonce.length + ct.length);
    blob.set(nonce); blob.set(ct, nonce.length);
    return { encrypted_private_key: b64(s, blob), salt: b64(s, salt) };
  }

  async function unlockPrivateKey(encryptedB64, saltB64, passphrase) {
    const s = await sodium();
    const blob = unb64(s, encryptedB64);
    const salt = unb64(s, saltB64);
    const key = s.crypto_pwhash(32, passphrase, salt,
      s.crypto_pwhash_OPSLIMIT_INTERACTIVE, s.crypto_pwhash_MEMLIMIT_INTERACTIVE,
      s.crypto_pwhash_ALG_ARGON2ID13);
    const nonce = blob.slice(0, s.crypto_secretbox_NONCEBYTES);
    const ct = blob.slice(s.crypto_secretbox_NONCEBYTES);
    try {
      return s.crypto_secretbox_open_easy(ct, nonce, key);
    } catch (e) {
      throw new Error("Wrong passphrase.");
    }
  }

  // ---- backup key (64 hex chars, shown in groups of 4) ----
  async function toBackupCode(sk) {
    const s = await sodium();
    return s.to_hex(sk).toUpperCase().match(/.{4}/g).join("-");
  }
  async function fromBackupCode(code) {
    const s = await sodium();
    const hex = code.replace(/[^0-9a-fA-F]/g, "").toLowerCase();
    if (hex.length !== 64) throw new Error("A backup key has 64 letters/numbers. Check it and try again.");
    return s.from_hex(hex);
  }

  async function publicKeyFor(sk) {
    const s = await sodium();
    return b64(s, s.crypto_scalarmult_base(sk));
  }

  // ---- keys kept for this tab only (gone when the tab closes) ----
  async function rememberKey(sk, pkB64) {
    const s = await sodium();
    sessionStorage.setItem(SK_STORE, b64(s, sk));
    sessionStorage.setItem(PK_STORE, pkB64);
  }
  async function recalledKey(expectedPkB64) {
    const skB64 = sessionStorage.getItem(SK_STORE);
    if (!skB64 || sessionStorage.getItem(PK_STORE) !== expectedPkB64) return null;
    const s = await sodium();
    return unb64(s, skB64);
  }
  function forgetKey() {
    sessionStorage.removeItem(SK_STORE);
    sessionStorage.removeItem(PK_STORE);
  }

  // ---- sealing (senders) and opening (oga) ----
  async function sealText(pkB64, text) {
    const s = await sodium();
    return b64(s, s.crypto_box_seal(s.from_string(text), unb64(s, pkB64)));
  }
  async function sealBytes(pkB64, u8) {
    const s = await sodium();
    return s.crypto_box_seal(u8, unb64(s, pkB64));
  }
  async function openText(pkB64, sk, ctB64) {
    const s = await sodium();
    return s.to_string(s.crypto_box_seal_open(unb64(s, ctB64), unb64(s, pkB64), sk));
  }
  async function openBytes(pkB64, sk, u8) {
    const s = await sodium();
    return s.crypto_box_seal_open(u8, unb64(s, pkB64), sk);
  }

  async function newKeyPair() {
    const s = await sodium();
    const kp = s.crypto_box_keypair();
    return { sk: kp.privateKey, pk: b64(s, kp.publicKey) };
  }

  function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const input = document.querySelector("input[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  async function postJSON(url, data) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      credentials: "same-origin",
      body: JSON.stringify(data),
    });
    let body = {};
    try { body = await r.json(); } catch (e) { /* ignore */ }
    if (!r.ok || !body.ok) throw new Error(body.error || "Something went wrong. Try again.");
    return body;
  }

  function downloadText(filename, text) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
  }

  window.SB = {
    sodium, lockPrivateKey, unlockPrivateKey, toBackupCode, fromBackupCode, publicKeyFor,
    rememberKey, recalledKey, forgetKey, sealText, sealBytes, openText, openBytes,
    newKeyPair, csrfToken, postJSON, downloadText,
  };
})();
