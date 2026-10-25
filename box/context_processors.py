from django.db.utils import OperationalError, ProgrammingError

from .models import BoxSettings


def box_settings(request):
    try:
        box = BoxSettings.load()
    except (OperationalError, ProgrammingError):  # before migrations run
        return {"box": None}
    ctx = {"box": box}
    # The locked private key is only ever sent to the owner's own pages.
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and box.owner_id == user.pk:
        ctx["key_data"] = {
            "public_key": box.public_key,
            "encrypted_private_key": box.encrypted_private_key,
            "salt": box.key_salt,
        }
    return ctx
