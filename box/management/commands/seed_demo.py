import base64
import json

from django.core.management.base import BaseCommand, CommandError
from nacl.public import PublicKey, SealedBox

from box.models import BoxSettings, Message

FAKE = [
    {"name": "Musa Ibrahim", "rank": "Cpl", "service_number": "", "unit": "Alpha Coy, 21 Bde", "phone": "", "cat": "welfare",
     "body": "The water tank in block C has been leaking for three weeks. We have reported it twice but nothing has happened."},
    {"name": "Chinedu Okafor", "rank": "LCpl", "service_number": "", "unit": "Bravo Coy, 21 Bde", "phone": "08030000000", "cat": "suggestion",
     "body": "Could we get a small reading room in the barracks? Many of us are writing exams and the rooms are too noisy at night."},
    {"name": "", "rank": "", "service_number": "", "unit": "Signals Pl", "phone": "", "cat": "complaint",
     "body": "Duty roster has not been rotated fairly this month. Same people keep getting weekend duties."},
    {"name": "", "rank": "", "service_number": "", "unit": "HQ Coy", "phone": "", "cat": "other",
     "body": "Thank you for creating this box. It's good to know someone is listening."},
]


class Command(BaseCommand):
    help = "Add a few FAKE (encrypted) messages for a demo. Run AFTER the oga has set up his key. Never on the real box."

    def handle(self, *args, **opts):
        box = BoxSettings.load()
        if not box.public_key:
            raise CommandError("The oga hasn't made his key yet. Log in as the oga first, then run this.")
        sealer = SealedBox(PublicKey(base64.b64decode(box.public_key)))
        for f in FAKE:
            payload = {"v": 1, "name": f["name"], "rank": f["rank"], "service_number": f["service_number"],
                       "unit": f["unit"], "phone": f["phone"], "body": f["body"]}
            ct = base64.b64encode(sealer.encrypt(json.dumps(payload).encode())).decode()
            Message.objects.create(category=f["cat"], payload=ct)
        self.stdout.write(self.style.SUCCESS(f"Added {len(FAKE)} fake, encrypted messages."))
