import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from box.models import BoxSettings


class Command(BaseCommand):
    help = (
        "Create (or reset) the oga's login and make it the ONLY account that can read messages.\n"
        "Use --reset-2fa if he lost his phone AND his backup codes (he'll set up 2-step login again)."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--password", help="Skip the prompt (handy for demos; avoid on real servers).")
        parser.add_argument("--reset-2fa", action="store_true", help="Remove his authenticator + backup codes.")
        parser.add_argument("--keep-password", action="store_true", help="Don't touch the password (use with --reset-2fa).")

    def handle(self, *args, **opts):
        User = get_user_model()
        username = opts["username"]
        user, created = User.objects.get_or_create(username=username)

        if not opts["keep_password"] or created:
            password = opts.get("password")
            if not password:
                password = getpass.getpass("Login password for the oga: ")
                if password != getpass.getpass("Again: "):
                    raise CommandError("Passwords don't match.")
            try:
                validate_password(password, user)
            except ValidationError as e:
                raise CommandError(" ".join(e.messages))
            user.set_password(password)

        # The oga is NOT staff/superuser: he can't open the developer admin.
        user.is_staff = False
        user.is_superuser = False
        user.save()

        if opts["reset_2fa"]:
            TOTPDevice.objects.filter(user=user).delete()
            StaticDevice.objects.filter(user=user).delete()
            self.stdout.write("2-step login reset. He'll be asked to set it up again at next login.")

        box = BoxSettings.load()
        box.owner = user
        box.save()
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} '{username}'. They own the box."))
