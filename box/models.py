import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BoxSettings(models.Model):
    """
    One row only (a "singleton"). Holds who owns the box, his encryption key,
    and how the box looks. The oga edits this from his dashboard.
    """

    THEME_CHOICES = [
        ("camo", "Army green (camo)"),
        ("night", "Night ops (dark)"),
        ("desert", "Desert (sand)"),
        ("plain", "Plain (light)"),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_box",
        help_text="The ONLY account that can read messages.",
    )

    # --- Personal touch ---
    # Just rank + name, no appointment: the box is personal to one CO.
    owner_rank = models.CharField(max_length=30, blank=True, default="", help_text='e.g. "Lt Col"')
    owner_name = models.CharField(max_length=80, blank=True, default="", help_text='e.g. "A. Bello"')
    title = models.CharField(max_length=80, default="Suggestion Box")
    subtitle = models.CharField(
        max_length=200, blank=True,
        default="Drop your complaint or suggestion. It goes straight to me and nobody else.",
    )
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default="camo")
    background_image_url = models.URLField(
        blank=True,
        help_text="Optional. Link to a background picture. Leave empty to use the theme's default.",
    )

    is_open = models.BooleanField(default=True, help_text="Untick to stop accepting new messages.")

    # --- Encryption keys (set up from the oga's browser) ---
    # Public key: senders' browsers lock messages with this.
    public_key = models.CharField(max_length=64, blank=True)
    # Private key, locked with the oga's passphrase. The server can't open it.
    encrypted_private_key = models.TextField(blank=True)
    key_salt = models.CharField(max_length=64, blank=True)
    key_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "box settings"
        verbose_name_plural = "box settings"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.pk = 1  # force a single row
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def has_key(self):
        return bool(self.public_key and self.encrypted_private_key)

    @property
    def ready(self):
        """Can the box accept messages right now?"""
        return self.is_open and self.has_key

    @property
    def recipient(self):
        """Who senders are told will read it."""
        return " ".join(p for p in (self.owner_rank.strip(), self.owner_name.strip()) if p) or "the commanding officer"


class Message(models.Model):
    """
    A message dropped in the box. Once saved, the sender never sees it again.
    There is deliberately NO sender account and NO 'my messages' page.

    Everything the sender typed (name, rank, service no., unit, phone, message)
    is inside `payload`, encrypted in the sender's browser with the oga's
    public key. The server, the host and the developer can't read it.
    """

    CATEGORY_CHOICES = [
        ("complaint", "Complaint"),
        ("suggestion", "Suggestion"),
        ("welfare", "Welfare"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("new", "New"),
        ("read", "Read"),
        ("resolved", "Resolved"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Plain (not secret) so the inbox can count and sort.
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="complaint")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="new")
    read_at = models.DateTimeField(null=True, blank=True)

    # Encrypted (base64 sealed box). Only the oga's private key opens these.
    payload = models.TextField()
    owner_note = models.TextField(blank=True, help_text="Oga's private note, also encrypted.")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} ({self.created_at:%d %b %Y %H:%M})"

    def mark_read(self):
        if self.status == "new":
            self.status = "read"
            self.read_at = timezone.now()
            self.save(update_fields=["status", "read_at"])


class Attachment(models.Model):
    """A photo, encrypted in the sender's browser. Stored in the database so it
    works on any host (no separate file storage needed)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    data = models.BinaryField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at"]
