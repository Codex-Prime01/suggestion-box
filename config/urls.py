from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Suggestion Box — developer admin"

urlpatterns = [
    path(f"{settings.ADMIN_URL_PREFIX}/", admin.site.urls),
    path("", include("box.urls")),
]
