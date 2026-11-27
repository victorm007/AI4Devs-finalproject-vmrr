from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"  # el que usan AUTH_USER_MODEL y las dependencias de las migraciones
    verbose_name = "Usuarios"
