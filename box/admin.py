from django.contrib import admin

from .models import BoxSettings

# NOTE: Message and Attachment are deliberately NOT registered here.
# They're encrypted anyway, but the developer admin has no business near them.


@admin.register(BoxSettings)
class BoxSettingsAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "theme", "is_open")
    # Changing the key here would make every message unreadable, so it's read-only.
    readonly_fields = ("public_key", "encrypted_private_key", "key_salt", "key_created_at")

    def has_add_permission(self, request):
        return not BoxSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
