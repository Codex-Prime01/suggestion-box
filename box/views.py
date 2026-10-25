import base64
import json
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_otp import match_token
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice
import segno

from .alerts import notify_new_message
from .forms import BoxSettingsForm, DropForm, OTPCodeForm, OwnerNoteForm, decode_b64, validate_photos
from .models import Attachment, BoxSettings, Message


# ---------- helpers ----------

def client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "")


def over_rate_limit(request):
    """Count attempts per IP per hour, in the cache only (never saved with a message)."""
    key = f"drops:{client_ip(request)}"
    cache.add(key, 0, 60 * 60)
    try:
        count = cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, 60 * 60)
        count = 1
    return count > settings.SUBMIT_RATE_LIMIT


def json_error(msg, status=400):
    return JsonResponse({"ok": False, "error": msg}, status=status)


def safe_next(request, default):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, require_https=request.is_secure()):
        return nxt
    return default


def has_confirmed_totp(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def owner_only(view):
    """Logged in with a password AND is the box owner. (2FA not checked yet.)"""

    @wraps(view)
    @login_required
    @never_cache
    def wrapper(request, *args, **kwargs):
        box = BoxSettings.load()
        if box.owner_id is None or request.user.pk != box.owner_id:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def owner_required(view):
    """Owner + passed 2FA + has an encryption key. Anyone else gets 403 — even superusers."""

    @wraps(view)
    @owner_only
    def wrapper(request, *args, **kwargs):
        if not request.user.is_verified():
            target = "box:otp_verify" if has_confirmed_totp(request.user) else "box:otp_setup"
            return redirect(f"{reverse(target)}?next={request.get_full_path()}")
        if not BoxSettings.load().has_key and view.__name__ != "key_setup":
            return redirect("box:key_setup")
        return view(request, *args, **kwargs)

    return wrapper


# ---------- public (sender) side ----------

def intro(request):
    """Landing page: tells soldiers what the box is and how it protects them."""
    return render(request, "box/intro.html")


@never_cache
def drop(request):
    box = BoxSettings.load()
    if not box.ready:
        if request.method == "POST":
            return json_error("This box isn't taking messages right now.", 503)
        return render(request, "box/closed.html", status=503)

    if request.method != "POST":
        return render(request, "box/drop.html", {"categories": Message.CATEGORY_CHOICES})

    form = DropForm(request.POST)
    if form.is_bot():
        return JsonResponse({"ok": True, "redirect": reverse("box:sent")})  # fool the bot
    if over_rate_limit(request):
        return json_error("Too many messages from this device. Try again later.", 429)
    if not form.is_valid():
        return json_error(" ".join(e for errs in form.errors.values() for e in errs))

    photos, err = validate_photos(request.FILES.getlist("photos"))
    if err:
        return json_error(err)

    with transaction.atomic():
        msg = Message.objects.create(category=form.cleaned_data["category"], payload=form.cleaned_data["payload"])
        for data in photos:
            Attachment.objects.create(message=msg, data=data, size=len(data))
        inbox_url = request.build_absolute_uri(reverse("box:inbox"))
        transaction.on_commit(lambda: notify_new_message(inbox_url))

    return JsonResponse({"ok": True, "redirect": reverse("box:sent")})


@never_cache
def sent(request):
    return render(request, "box/sent.html")


# ---------- owner: two-step login (2FA) ----------

@owner_only
def otp_setup(request):
    """First login: link an authenticator app (Google Authenticator, Authy, Microsoft Authenticator...)."""
    user = request.user
    if has_confirmed_totp(user):
        return redirect("box:otp_verify")
    device, _ = TOTPDevice.objects.get_or_create(user=user, confirmed=False, defaults={"name": "Authenticator app"})

    form = OTPCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if device.verify_token(form.cleaned_data["code"]):
            device.confirmed = True
            device.save()
            otp_login(request, device)
            # Backup codes for when the phone is lost. Shown once.
            static, _ = StaticDevice.objects.get_or_create(user=user, name="Backup codes")
            static.token_set.all().delete()
            codes = [StaticToken.random_token() for _ in range(8)]
            for c in codes:
                static.token_set.create(token=c)
            return render(request, "box/otp_backup_codes.html", {"codes": codes, "next": safe_next(request, reverse("box:inbox"))})
        form.add_error("code", "That code didn't work. Check your phone's time is correct and try the newest code.")

    # omitsize: no fixed width/height, so the QR scales to fit its box instead of getting cut off
    qr_svg = segno.make(device.config_url, error="m").svg_inline(
        omitsize=True, svgclass="block w-full", dark="#111", light="#fff"
    )
    secret_b32 = base64.b32encode(device.bin_key).decode().rstrip("=")
    return render(request, "box/otp_setup.html", {
        "form": form,
        "qr_svg": mark_safe(qr_svg),  # generated by segno from our own data, safe to inline
        "secret": " ".join(secret_b32[i:i + 4] for i in range(0, len(secret_b32), 4)),
        "next": safe_next(request, reverse("box:inbox")),
    })


@owner_only
def otp_verify(request):
    if not has_confirmed_totp(request.user):
        return redirect("box:otp_setup")
    if request.user.is_verified():
        return redirect(safe_next(request, reverse("box:inbox")))
    form = OTPCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        device = match_token(request.user, form.cleaned_data["code"])
        if device:
            otp_login(request, device)
            return redirect(safe_next(request, reverse("box:inbox")))
        form.add_error("code", "Wrong or expired code. Wait for a new one and try again.")
    return render(request, "box/otp_verify.html", {"form": form, "next": safe_next(request, reverse("box:inbox"))})


# ---------- owner: encryption key ----------

@owner_required
def key_setup(request):
    """First-time key creation. The browser makes the keys; we only store the
    public key and the passphrase-locked private key."""
    box = BoxSettings.load()
    if request.method == "POST":
        if box.has_key:
            return json_error("A key already exists. Use 'Change passphrase' instead.", 409)
        try:
            data = json.loads(request.body)
        except ValueError:
            return json_error("Bad request.")
        pk, epk, salt = data.get("public_key", ""), data.get("encrypted_private_key", ""), data.get("salt", "")
        pk_raw = decode_b64(pk)
        if pk_raw is None or len(pk_raw) != 32 or decode_b64(epk) is None or decode_b64(salt) is None:
            return json_error("Bad key data.")
        box.public_key, box.encrypted_private_key, box.key_salt = pk, epk, salt
        box.key_created_at = timezone.now()
        box.save()
        return JsonResponse({"ok": True, "redirect": reverse("box:settings")})
    if box.has_key:
        return redirect("box:inbox")
    return render(request, "box/key_setup.html")


@owner_required
@require_POST
def key_rewrap(request):
    """Change passphrase / recover with backup key. The KEY stays the same
    (so old messages still open); only its passphrase lock changes."""
    box = BoxSettings.load()
    try:
        data = json.loads(request.body)
    except ValueError:
        return json_error("Bad request.")
    if data.get("public_key") != box.public_key:
        return json_error("That backup key doesn't belong to this box.", 409)
    epk, salt = data.get("encrypted_private_key", ""), data.get("salt", "")
    if decode_b64(epk) is None or decode_b64(salt) is None:
        return json_error("Bad key data.")
    box.encrypted_private_key, box.key_salt = epk, salt
    box.save(update_fields=["encrypted_private_key", "key_salt"])
    return JsonResponse({"ok": True})


@owner_required
def key_unlock(request):
    return render(request, "box/unlock.html", {"next": safe_next(request, reverse("box:inbox"))})


@owner_required
def key_manage(request):
    return render(request, "box/key_manage.html")


# ---------- owner: inbox ----------

@owner_required
def inbox(request):
    qs = Message.objects.annotate(photo_count=Count("attachments"))
    status = request.GET.get("status", "")
    category = request.GET.get("category", "")
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)
    counts = Message.objects.aggregate(
        total=Count("id"),
        new=Count("id", filter=Q(status="new")),
        resolved=Count("id", filter=Q(status="resolved")),
    )
    return render(request, "box/inbox.html", {
        "messages_list": qs[:300],
        "counts": counts,
        "filters": {"status": status, "category": category},
        "status_choices": Message.STATUS_CHOICES,
        "category_choices": Message.CATEGORY_CHOICES,
    })


@owner_required
def message_detail(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    if request.method == "POST":
        form = OwnerNoteForm(request.POST, instance=msg)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved.")
            return redirect("box:detail", pk=msg.pk)
    else:
        msg.mark_read()
        form = OwnerNoteForm(instance=msg)
    return render(request, "box/detail.html", {
        "msg": msg, "form": form, "attachments": msg.attachments.only("id", "size"),
    })


@owner_required
def attachment_data(request, pk):
    att = get_object_or_404(Attachment, pk=pk)
    resp = HttpResponse(bytes(att.data), content_type="application/octet-stream")
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@owner_required
@require_POST
def message_delete(request, pk):
    get_object_or_404(Message, pk=pk).delete()
    messages.success(request, "Message deleted for good.")
    return redirect("box:inbox")


@owner_required
def box_settings(request):
    box = BoxSettings.load()
    if request.method == "POST":
        form = BoxSettingsForm(request.POST, instance=box)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated.")
            return redirect("box:settings")
    else:
        form = BoxSettingsForm(instance=box)
    return render(request, "box/settings.html", {
        "form": form,
        "share_url": request.build_absolute_uri(reverse("box:intro")),
        "alerts_on": bool(settings.ALERT_EMAIL or settings.TELEGRAM_BOT_TOKEN),
    })


# ---------- PWA bits ----------

def manifest(request):
    box = BoxSettings.load()
    data = {
        "name": box.title, "short_name": box.title[:12], "start_url": reverse("box:intro"),
        "display": "standalone", "background_color": "#2f3a24", "theme_color": "#2f3a24",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icons/icon.svg", "sizes": "any", "type": "image/svg+xml"},
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")
