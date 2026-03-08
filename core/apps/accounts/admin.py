from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "rating", "level", "is_level_manual", "created_at", "updated_at")
    list_filter = ("level", "is_level_manual")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-rating",)
