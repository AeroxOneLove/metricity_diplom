from django.contrib import admin

from .models import UserProfile, UserRatingEvent


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "rating", "level", "is_level_manual", "created_at", "updated_at")
    list_filter = ("level", "is_level_manual")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-rating",)


@admin.register(UserRatingEvent)
class UserRatingEventAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "delta", "reason", "complaint", "incoming_report", "created_at")
    list_filter = ("reason",)
    search_fields = ("user__username", "user__email", "complaint__id", "incoming_report__id")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
