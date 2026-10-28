# Split the free-text display name into rank + name (client: no appointment, just rank and name).
from django.db import migrations, models


def copy_old_name(apps, schema_editor):
    # Keep anything already typed, so nothing is lost. The oga can split it in Settings.
    BoxSettings = apps.get_model("box", "BoxSettings")
    for box in BoxSettings.objects.exclude(owner_display_name=""):
        box.owner_name = box.owner_display_name[:80]
        box.save(update_fields=["owner_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("box", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="boxsettings",
            name="owner_rank",
            field=models.CharField(blank=True, default="", help_text='e.g. "Lt Col"', max_length=30),
        ),
        migrations.AddField(
            model_name="boxsettings",
            name="owner_name",
            field=models.CharField(blank=True, default="", help_text='e.g. "A. Bello"', max_length=80),
        ),
        migrations.RunPython(copy_old_name, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="boxsettings",
            name="owner_display_name",
        ),
    ]
