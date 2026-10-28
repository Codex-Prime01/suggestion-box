import base64
import binascii

from django import forms

from .models import BoxSettings, Message

INPUT = "w-full rounded-lg border border-black/15 bg-white/90 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600"

MAX_PAYLOAD_BYTES = 64 * 1024        # encrypted text part
MAX_PHOTOS = 3
MAX_PHOTO_BYTES = 4 * 1024 * 1024    # each, after encryption
SEAL_OVERHEAD = 48                   # libsodium sealed box adds 48 bytes


def decode_b64(value):
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None


class DropForm(forms.Form):
    """
    What the server receives from a sender. The real content is already
    encrypted in the browser, so the server only checks shape and size.
    """

    category = forms.ChoiceField(choices=Message.CATEGORY_CHOICES)
    payload = forms.CharField(max_length=MAX_PAYLOAD_BYTES * 2)
    website = forms.CharField(required=False)  # honeypot

    def clean_payload(self):
        raw = decode_b64(self.cleaned_data["payload"])
        if raw is None or not (SEAL_OVERHEAD < len(raw) <= MAX_PAYLOAD_BYTES):
            raise forms.ValidationError("Message could not be read. Refresh the page and try again.")
        return self.cleaned_data["payload"]

    def is_bot(self):
        return bool(self.data.get("website"))


def validate_photos(files):
    """Returns (list_of_bytes, error_message)."""
    if len(files) > MAX_PHOTOS:
        return None, f"You can attach at most {MAX_PHOTOS} photos."
    out = []
    for f in files:
        if f.size > MAX_PHOTO_BYTES or f.size <= SEAL_OVERHEAD:
            return None, "One of the photos is too big. Try a smaller one."
        out.append(f.read())
    return out, None


class OwnerNoteForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["status", "owner_note"]
        widgets = {"owner_note": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].widget.attrs["class"] = INPUT

    def clean_owner_note(self):
        note = self.cleaned_data.get("owner_note", "")
        if note and decode_b64(note) is None:
            raise forms.ValidationError("Note must be encrypted.")
        return note


class BoxSettingsForm(forms.ModelForm):
    class Meta:
        model = BoxSettings
        fields = [
            "owner_rank", "owner_name", "title", "subtitle", "theme", "background_image_url", "is_open",
        ]
        labels = {"owner_rank": "Your rank", "owner_name": "Your name"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", INPUT)


class OTPCodeForm(forms.Form):
    code = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            "class": INPUT + " text-center text-2xl tracking-[0.4em]",
            "autocomplete": "one-time-code", "inputmode": "numeric", "autofocus": True,
        }),
    )

    def clean_code(self):
        return self.cleaned_data["code"].replace(" ", "").replace("-", "").strip()
