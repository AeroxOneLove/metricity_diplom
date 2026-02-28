from django.apps import AppConfig


class ModerationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.apps.moderation"
    label = "moderation"
    verbose_name = "Moderation"
