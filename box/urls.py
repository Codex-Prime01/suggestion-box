from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "box"
P = settings.OWNER_URL_PREFIX

urlpatterns = [
    # Public: anyone with the link
    path("", views.intro, name="intro"),
    path("drop/", views.drop, name="drop"),
    path("sent/", views.sent, name="sent"),
    path("manifest.webmanifest", views.manifest, name="manifest"),

    # Owner only
    path(f"{P}/manifest.webmanifest", views.owner_manifest, name="owner_manifest"),
    path(f"{P}/login/", auth_views.LoginView.as_view(template_name="box/login.html", redirect_authenticated_user=False), name="login"),
    path(f"{P}/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(f"{P}/2fa/setup/", views.otp_setup, name="otp_setup"),
    path(f"{P}/2fa/", views.otp_verify, name="otp_verify"),
    path(f"{P}/", views.inbox, name="inbox"),
    path(f"{P}/m/<uuid:pk>/", views.message_detail, name="detail"),
    path(f"{P}/m/<uuid:pk>/delete/", views.message_delete, name="delete"),
    path(f"{P}/a/<uuid:pk>/", views.attachment_data, name="attachment"),
    path(f"{P}/settings/", views.box_settings, name="settings"),
    path(f"{P}/key/setup/", views.key_setup, name="key_setup"),
    path(f"{P}/key/unlock/", views.key_unlock, name="key_unlock"),
    path(f"{P}/key/manage/", views.key_manage, name="key_manage"),
    path(f"{P}/key/rewrap/", views.key_rewrap, name="key_rewrap"),
]
