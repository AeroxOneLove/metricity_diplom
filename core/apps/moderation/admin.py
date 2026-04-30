from django.contrib import admin

from .models import ModerationDecision


@admin.register(ModerationDecision)
class ModerationDecisionAdmin(admin.ModelAdmin):
    list_display = ("incoming", "moderator", "decision", "final_category", "timestamps")
    list_filter = ("decision", "final_category")
    search_fields = ("incoming__id", "moderator__username", "moderator__email")
    readonly_fields = ("timestamps",)
    ordering = ("-timestamps",)
    date_hierarchy = "timestamps"
