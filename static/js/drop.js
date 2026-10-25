/*
  Sender side: a 2-step form (About you → Message).
  On send, the message and photos are locked in the browser with the oga's
  public key, and only the locked version goes to the server.
*/
(function () {
  "use strict";
  const form = document.getElementById("drop-form");
  if (!form) return;

  const pk = form.dataset.publicKey;
  const $ = (id) => document.getElementById(id);
  const btn = form.querySelector("button[type=submit]");
  const errorBox = $("form-error");
  const photoInput = $("photos");
  const photoList = $("photo-list");
  const MAX_PHOTOS = 3;
  const MAX_SIDE = 1600;

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.hidden = false;
    errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function clearError() { errorBox.hidden = true; }
  function val(name) {
    const el = form.elements[name];
    if (!el) return "";
    return (el.value || "").trim();  // RadioNodeList.value works for radios too
  }

  // ---------- steps ----------
  function goTo(step) {
    clearError();
    $("step-1").hidden = step !== 1;
    $("step-2").hidden = step !== 2;
    $("bar-2").classList.toggle("btn", step === 2);
    $("bar-2").classList.toggle("chip", step !== 2);
    $("step-label").textContent = step === 1 ? "Step 1 of 2 · About you" : "Step 2 of 2 · Your message";
    window.scrollTo({ top: 0, behavior: "smooth" });
    (step === 1 ? $("unit") : $("body")).focus({ preventScroll: true });
  }

  $("to-step-2").addEventListener("click", () => {
    if (!val("unit")) { showError("Please fill in your unit."); $("unit").focus(); return; }
    const who = [val("rank"), val("sender_name")].filter(Boolean).join(" ") || "Name not given";
    $("from-summary").textContent = who + " · " + val("unit");
    goTo(2);
  });
  $("to-step-1").addEventListener("click", () => goTo(1));
  $("from-chip").addEventListener("click", () => goTo(1));
  // Enter in a step-1 field moves on instead of submitting.
  $("step-1").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); $("to-step-2").click(); }
  });

  // ---------- photos ----------
  photoInput.addEventListener("change", () => {
    const files = Array.from(photoInput.files);
    photoList.textContent = "";
    if (files.length > MAX_PHOTOS) {
      showError(`You can attach at most ${MAX_PHOTOS} photos.`);
      photoInput.value = "";
      return;
    }
    clearError();
    files.forEach((f) => {
      const li = document.createElement("li");
      li.textContent = "📷 " + f.name;
      photoList.appendChild(li);
    });
  });

  // Re-draw the photo on a canvas: shrinks it AND removes hidden data such as
  // GPS location, phone model and time (EXIF). Then lock it.
  async function preparePhoto(file) {
    if (!file.type.startsWith("image/")) throw new Error(`"${file.name}" is not a photo.`);
    let bitmap;
    try {
      bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    } catch (e) {
      throw new Error(`Couldn't open "${file.name}". Try a JPG or PNG.`);
    }
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.85));
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const sealed = await SB.sealBytes(pk, bytes);
    return new Blob([sealed], { type: "application/octet-stream" });
  }

  // ---------- send ----------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();

    if (!val("unit")) { goTo(1); return showError("Please fill in your unit."); }
    if (val("body").length < 5) return showError("Your message is too short.");
    const files = Array.from(photoInput.files);
    if (files.length > MAX_PHOTOS) return showError(`You can attach at most ${MAX_PHOTOS} photos.`);

    btn.disabled = true;
    const oldLabel = btn.textContent;
    btn.textContent = "Locking your message…";

    try {
      const payload = JSON.stringify({
        v: 1,
        name: val("sender_name"),
        rank: val("rank"),
        service_number: val("service_number"),
        unit: val("unit"),
        phone: val("phone"),
        body: val("body"),
      });

      const fd = new FormData();
      fd.append("category", val("category"));
      fd.append("payload", await SB.sealText(pk, payload));
      fd.append("website", val("website"));
      for (const f of files) fd.append("photos", await preparePhoto(f), "photo.bin");

      btn.textContent = "Sending…";
      const r = await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": SB.csrfToken() },
        credentials: "same-origin",
        body: fd,
      });
      let data = {};
      try { data = await r.json(); } catch (_) { /* ignore */ }
      if (!r.ok || !data.ok) throw new Error(data.error || "Couldn't send. Check your network and try again.");

      form.reset();  // wipe the typed text from the page
      window.location.replace(data.redirect);  // Back button can't return to the filled form
    } catch (err) {
      showError(err.message);
      btn.disabled = false;
      btn.textContent = oldLabel;
    }
  });
})();
