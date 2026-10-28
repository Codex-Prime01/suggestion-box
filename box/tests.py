"""
Run with:  python manage.py test box

These tests act like the browser by encrypting with PyNaCl (same maths as
libsodium in the browser), so we can prove the server never sees plain text.
"""
import base64
import json
import time

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from nacl.public import PrivateKey, SealedBox

from .models import Attachment, BoxSettings, Message

User = get_user_model()
SECRET = "Our water tank has been broken for 3 weeks."


def make_box(owner=None):
    sk = PrivateKey.generate()
    box = BoxSettings.load()
    box.owner = owner
    box.public_key = base64.b64encode(bytes(sk.public_key)).decode()
    box.encrypted_private_key = base64.b64encode(b"x" * 72).decode()  # not used server-side
    box.key_salt = base64.b64encode(b"s" * 16).decode()
    box.save()
    return box, sk


def seal(box, obj):
    from nacl.public import PublicKey
    pk = PublicKey(base64.b64decode(box.public_key))
    data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
    return SealedBox(pk).encrypt(data)


def good_post(box, **extra):
    payload = {"v": 1, "name": "Musa Ali", "rank": "Cpl", "service_number": "", "unit": "21 Bde", "phone": "", "body": SECRET}
    data = {"category": "complaint", "payload": base64.b64encode(seal(box, payload)).decode()}
    data.update(extra)
    return data


def login_verified(client, user):
    """Log in AND pass 2-step login, like the oga would."""
    device = TOTPDevice.objects.create(user=user, name="t", confirmed=True)
    client.force_login(user)
    session = client.session
    session["otp_device_id"] = device.persistent_id
    session.save()
    return device


class SenderSideTests(TestCase):
    def setUp(self):
        cache.clear()
        self.box, self.sk = make_box()

    def post(self, data, **kw):
        return self.client.post(reverse("box:drop"), data, **kw)

    def test_intro_page_links_to_form(self):
        r = self.client.get(reverse("box:intro"))
        self.assertContains(r, reverse("box:drop"))
        self.assertContains(r, "the commanding officer")  # no name set yet -> generic

    def test_intro_hero_video_is_self_hosted_with_fallback(self):
        # rule 8: self-hosted only. The SVG story stays as the fallback (no JS, reduced motion, data saver)
        r = self.client.get(reverse("box:intro"))
        self.assertContains(r, 'preload="none"')
        self.assertContains(r, "/static/video/hero-loop.webm")
        self.assertContains(r, "/static/video/hero-loop.mp4")
        self.assertContains(r, 'class="hero-art')
        self.assertNotContains(r, "<video autoplay")
        self.assertNotContains(r, "{#")  # multi-line {# #} comments leak onto the page
        self.assertIn("media-src 'self'", r["Content-Security-Policy"])

    def test_owner_name_shows_when_set(self):
        self.box.owner_rank, self.box.owner_name = "Lt Col", "A. Bello"; self.box.save()
        self.assertContains(self.client.get(reverse("box:intro")), "Lt Col A. Bello")
        self.assertContains(self.client.get(reverse("box:drop")), "Goes straight to Lt Col A. Bello")

    def test_recipient_is_rank_and_name_only(self):
        self.assertEqual(self.box.recipient, "the commanding officer")
        self.box.owner_rank = "Lt Col"
        self.assertEqual(self.box.recipient, "Lt Col")
        self.box.owner_name = "A. Bello"
        self.assertEqual(self.box.recipient, "Lt Col A. Bello")

    def test_number_field_says_svcno_armyno(self):
        self.assertContains(self.client.get(reverse("box:drop")), "SvcNo/ArmyNo")

    def test_manifest(self):
        r = self.client.get(reverse("box:manifest"))
        self.assertEqual(r.json()["name"], "Suggestion Box")

    def test_drop_page_loads_with_public_key(self):
        r = self.client.get(reverse("box:drop"))
        self.assertContains(r, self.box.public_key)

    def test_drop_page_never_leaks_locked_private_key(self):
        r = self.client.get(reverse("box:drop"))
        self.assertNotContains(r, self.box.encrypted_private_key)

    def test_message_saved_encrypted_only(self):
        r = self.post(good_post(self.box))
        self.assertEqual(r.json()["redirect"], reverse("box:sent"))
        msg = Message.objects.get()
        self.assertNotIn("water tank", msg.payload)
        # ...but the oga's private key opens it
        opened = json.loads(SealedBox(self.sk).decrypt(base64.b64decode(msg.payload)))
        self.assertEqual(opened["body"], SECRET)

    def test_garbage_payload_rejected(self):
        r = self.post(good_post(self.box, payload="hello not encrypted"))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Message.objects.exists())

    def test_photos_saved_encrypted(self):
        photo = SimpleUploadedFile("p.bin", seal(self.box, b"\xff\xd8 fake jpeg bytes"))
        r = self.post({**good_post(self.box), "photos": [photo]})
        self.assertEqual(r.status_code, 200)
        att = Attachment.objects.get()
        self.assertEqual(SealedBox(self.sk).decrypt(bytes(att.data)), b"\xff\xd8 fake jpeg bytes")

    def test_too_many_photos(self):
        photos = [SimpleUploadedFile(f"{i}.bin", seal(self.box, b"img")) for i in range(4)]
        r = self.post({**good_post(self.box), "photos": photos})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Message.objects.exists())

    def test_honeypot_blocks_bots_silently(self):
        r = self.post(good_post(self.box, website="spam.com"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Message.objects.exists())

    @override_settings(SUBMIT_RATE_LIMIT=2)
    def test_rate_limit(self):
        for _ in range(2):
            self.assertEqual(self.post(good_post(self.box)).status_code, 200)
        self.assertEqual(self.post(good_post(self.box)).status_code, 429)
        self.assertEqual(Message.objects.count(), 2)

    def test_closed_box(self):
        self.box.is_open = False; self.box.save()
        self.assertEqual(self.client.get(reverse("box:drop")).status_code, 503)

    def test_box_closed_until_key_exists(self):
        self.box.public_key = ""; self.box.save()
        self.assertEqual(self.client.get(reverse("box:drop")).status_code, 503)

    def test_sent_page_has_no_content(self):
        self.post(good_post(self.box))
        self.assertNotContains(self.client.get(reverse("box:sent")), "water")

    def test_security_headers_self_only(self):
        csp = self.client.get(reverse("box:drop"))["Content-Security-Policy"]
        self.assertIn("script-src 'self' 'wasm-unsafe-eval'", csp)
        self.assertNotIn("jsdelivr", csp)
        self.assertNotIn("unsafe-eval'", csp.replace("wasm-unsafe-eval'", ""))

    @override_settings(ALERT_EMAIL="oga@example.com", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_alert_email_has_no_content_and_cools_down(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.post(good_post(self.box))
        with self.captureOnCommitCallbacks(execute=True):
            self.post(good_post(self.box))
        self.assertEqual(len(mail.outbox), 1)  # second one is inside the cooldown
        email = mail.outbox[0]
        for secret in ("water", "Musa", "21 Bde"):
            self.assertNotIn(secret, email.subject + email.body)


class OwnerSideTests(TestCase):
    def setUp(self):
        cache.clear()
        self.oga = User.objects.create_user("oga", password="StrongPass!234")
        self.other = User.objects.create_user("commander", password="StrongPass!234")
        self.dev = User.objects.create_superuser("dev", password="StrongPass!234")
        self.box, self.sk = make_box(owner=self.oga)
        self.client.post(reverse("box:drop"), {**good_post(self.box), "photos": [SimpleUploadedFile("p", seal(self.box, b"img"))]})
        self.msg = Message.objects.get()
        self.att = Attachment.objects.get()

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("box:inbox"))
        self.assertIn(reverse("box:login"), r["Location"])

    def test_other_user_forbidden_everywhere(self):
        self.client.force_login(self.other)
        for url in [reverse("box:inbox"), reverse("box:detail", args=[self.msg.pk]),
                    reverse("box:attachment", args=[self.att.pk]), reverse("box:settings"),
                    reverse("box:key_unlock")]:
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_even_superuser_forbidden(self):
        self.client.force_login(self.dev)
        self.assertEqual(self.client.get(reverse("box:inbox")).status_code, 403)

    def test_locked_key_only_on_owner_pages(self):
        login_verified(self.client, self.oga)
        self.assertContains(self.client.get(reverse("box:key_unlock")), self.box.encrypted_private_key)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("box:drop")), self.box.encrypted_private_key)

    def test_owner_inbox_and_detail(self):
        login_verified(self.client, self.oga)
        self.assertContains(self.client.get(reverse("box:inbox")), self.msg.payload)
        self.client.get(reverse("box:detail", args=[self.msg.pk]))
        self.msg.refresh_from_db()
        self.assertEqual(self.msg.status, "read")

    def test_owner_gets_attachment_bytes(self):
        login_verified(self.client, self.oga)
        r = self.client.get(reverse("box:attachment", args=[self.att.pk]))
        self.assertEqual(SealedBox(self.sk).decrypt(r.content), b"img")

    def test_note_must_be_encrypted(self):
        login_verified(self.client, self.oga)
        url = reverse("box:detail", args=[self.msg.pk])
        self.client.post(url, {"status": "resolved", "owner_note": "plain text!!"})
        self.msg.refresh_from_db()
        self.assertEqual(self.msg.owner_note, "")
        note = base64.b64encode(seal(self.box, b"fixed")).decode()
        self.client.post(url, {"status": "resolved", "owner_note": note})
        self.msg.refresh_from_db()
        self.assertEqual(self.msg.status, "resolved")

    def test_owner_can_delete(self):
        login_verified(self.client, self.oga)
        self.client.post(reverse("box:delete", args=[self.msg.pk]))
        self.assertFalse(Message.objects.exists())
        self.assertFalse(Attachment.objects.exists())

    def test_clear_needs_typed_confirm(self):
        login_verified(self.client, self.oga)
        self.client.post(reverse("box:clear"), {"confirm": "yes"})
        self.client.post(reverse("box:clear"), {})
        self.assertTrue(Message.objects.exists())

    def test_clear_with_no_filter_deletes_all(self):
        self.client.post(reverse("box:drop"), good_post(self.box, category="suggestion"))
        login_verified(self.client, self.oga)
        self.client.post(reverse("box:clear"), {"confirm": "DELETE"})
        self.assertFalse(Message.objects.exists())
        self.assertFalse(Attachment.objects.exists())

    def test_clear_only_hits_filtered_messages(self):
        self.client.post(reverse("box:drop"), good_post(self.box, category="suggestion"))
        Message.objects.filter(category="complaint").update(status="resolved")
        login_verified(self.client, self.oga)
        self.client.post(reverse("box:clear"), {"status": "resolved", "category": "", "confirm": "DELETE"})
        self.assertEqual(list(Message.objects.values_list("category", flat=True)), ["suggestion"])

    def test_clear_is_post_and_owner_only(self):
        login_verified(self.client, self.oga)
        self.assertEqual(self.client.get(reverse("box:clear")).status_code, 405)
        for user in (self.other, self.dev):
            self.client.force_login(user)
            self.assertEqual(self.client.post(reverse("box:clear"), {"confirm": "DELETE"}).status_code, 403)
        self.assertTrue(Message.objects.exists())

    def test_rewrap_needs_same_public_key(self):
        login_verified(self.client, self.oga)
        url = reverse("box:key_rewrap")
        new = {"encrypted_private_key": base64.b64encode(b"n" * 72).decode(), "salt": base64.b64encode(b"t" * 16).decode()}
        r = self.client.post(url, {**new, "public_key": "AAAA"}, content_type="application/json")
        self.assertEqual(r.status_code, 409)
        r = self.client.post(url, {**new, "public_key": self.box.public_key}, content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(BoxSettings.load().encrypted_private_key, new["encrypted_private_key"])

    def test_key_setup_cannot_overwrite_existing_key(self):
        login_verified(self.client, self.oga)
        r = self.client.post(reverse("box:key_setup"), {"public_key": base64.b64encode(b"k" * 32).decode(),
                             "encrypted_private_key": "eA==", "salt": "eA=="}, content_type="application/json")
        self.assertEqual(r.status_code, 409)

    def test_owner_settings_save(self):
        login_verified(self.client, self.oga)
        self.client.post(reverse("box:settings"), {"owner_rank": "Lt Col", "owner_name": "A. Bello", "title": "T", "theme": "night", "is_open": "on"})
        self.assertEqual(BoxSettings.load().theme, "night")
        self.assertEqual(BoxSettings.load().recipient, "Lt Col A. Bello")
        self.assertContains(self.client.get(reverse("box:drop")), "theme-night")

    def test_owner_pages_not_cached(self):
        login_verified(self.client, self.oga)
        self.assertIn("no-store", self.client.get(reverse("box:inbox"))["Cache-Control"])


class PasswordOnlyLoginTests(TestCase):
    """Default: OWNER_2FA is off, so the oga logs in with username + password only."""

    def setUp(self):
        cache.clear()
        self.oga = User.objects.create_user("oga", password="StrongPass!234")
        self.box, self.sk = make_box(owner=self.oga)

    @override_settings(OWNER_2FA=False)
    def test_password_alone_opens_inbox(self):
        self.client.force_login(self.oga)
        self.assertEqual(self.client.get(reverse("box:inbox")).status_code, 200)

    @override_settings(OWNER_2FA=False)
    def test_old_2fa_links_send_him_to_inbox(self):
        self.client.force_login(self.oga)
        for name in ("box:otp_setup", "box:otp_verify"):
            self.assertRedirects(self.client.get(reverse(name)), reverse("box:inbox"))

    @override_settings(OWNER_2FA=False)
    def test_still_owner_only_without_2fa(self):
        other = User.objects.create_superuser("boss", password="StrongPass!234")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("box:inbox")).status_code, 403)

    def test_owner_app_opens_his_inbox(self):
        m = self.client.get(reverse("box:owner_manifest")).json()
        self.assertEqual(m["start_url"], reverse("box:inbox"))
        self.assertEqual(m["scope"], reverse("box:inbox"))
        # his pages point to his app; the public page keeps the soldiers' app
        self.client.force_login(self.oga)
        self.assertContains(self.client.get(reverse("box:inbox")), reverse("box:owner_manifest"))
        self.assertContains(self.client.get(reverse("box:login")), reverse("box:owner_manifest"))
        intro = self.client.get(reverse("box:intro"))
        self.assertContains(intro, reverse("box:manifest"))
        self.assertNotContains(intro, reverse("box:owner_manifest"))  # never leak the secret path


@override_settings(OWNER_2FA=True)
class TwoStepLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.oga = User.objects.create_user("oga", password="StrongPass!234")
        self.box, self.sk = make_box(owner=self.oga)

    def test_password_alone_is_not_enough(self):
        self.client.force_login(self.oga)
        r = self.client.get(reverse("box:inbox"))
        self.assertTrue(r["Location"].startswith(reverse("box:otp_setup")))

    def test_setup_with_real_code_then_backup_codes(self):
        self.client.force_login(self.oga)
        self.client.get(reverse("box:otp_setup"))
        device = TOTPDevice.objects.get(user=self.oga)
        code = f"{totp(device.bin_key):06d}"
        r = self.client.post(reverse("box:otp_setup"), {"code": code})
        self.assertContains(r, "2-step login is on")
        self.assertEqual(len(r.context["codes"]), 8)
        self.assertEqual(self.client.get(reverse("box:inbox")).status_code, 200)
        # next login: must verify, and a backup code works once
        backup = r.context["codes"][0]
        self.client.logout(); self.client.force_login(self.oga)
        self.assertTrue(self.client.get(reverse("box:inbox"))["Location"].startswith(reverse("box:otp_verify")))
        self.client.post(reverse("box:otp_verify"), {"code": "000000"})
        self.assertNotEqual(self.client.get(reverse("box:inbox")).status_code, 200)
        time.sleep(1.2)  # django-otp slows down guessing after a wrong code
        self.client.post(reverse("box:otp_verify"), {"code": backup})
        self.assertEqual(self.client.get(reverse("box:inbox")).status_code, 200)

    def test_setup_qr_scales_to_fit(self):
        # a fixed-size SVG overflowed its box and got cut off, so the QR couldn't be scanned
        self.client.force_login(self.oga)
        svg = str(self.client.get(reverse("box:otp_setup")).context["qr_svg"])
        self.assertIn("viewBox", svg)
        self.assertNotRegex(svg, r"<svg[^>]*\swidth=")

    def test_wrong_setup_code_rejected(self):
        self.client.force_login(self.oga)
        self.client.get(reverse("box:otp_setup"))
        self.client.post(reverse("box:otp_setup"), {"code": "123456"})
        self.assertFalse(TOTPDevice.objects.filter(user=self.oga, confirmed=True).exists())

    def test_other_user_cannot_reach_2fa_pages(self):
        other = User.objects.create_user("x", password="StrongPass!234")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("box:otp_setup")).status_code, 403)

    @override_settings(AXES_FAILURE_LIMIT=3)
    def test_lockout_after_wrong_passwords(self):
        url = reverse("box:login")
        for _ in range(3):
            self.client.post(url, {"username": "oga", "password": "wrong-password"}, REMOTE_ADDR="1.2.3.4")
        r = self.client.post(url, {"username": "oga", "password": "StrongPass!234"}, REMOTE_ADDR="1.2.3.4")
        self.assertContains(r, "Too many tries", status_code=429)


class FirstTimeSetupTests(TestCase):
    def test_new_owner_sent_to_key_setup(self):
        oga = User.objects.create_user("oga", password="StrongPass!234")
        box = BoxSettings.load(); box.owner = oga; box.save()
        login_verified(self.client, oga)
        self.assertRedirects(self.client.get(reverse("box:inbox")), reverse("box:key_setup"))
        pk = base64.b64encode(bytes(PrivateKey.generate().public_key)).decode()
        r = self.client.post(reverse("box:key_setup"), {"public_key": pk, "encrypted_private_key": "eA==", "salt": "eA=="},
                             content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(BoxSettings.load().has_key)
