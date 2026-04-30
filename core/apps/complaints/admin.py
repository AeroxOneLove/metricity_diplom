from django.contrib import admin

from .models import Complaint, ComplaintImportanceVote, IncomingReport, StackReport


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "status",
        "lat",
        "lon",
        "stack_count",
        "priority_score",
        "ai_verified",
        "created_at",
    )
    list_filter = ("category", "status", "ai_verified")
    search_fields = ("cell_id",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-priority_score", "-created_at")
    date_hierarchy = "created_at"


@admin.register(IncomingReport)
class IncomingReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "declared_category",
        "status",
        "ai_pred_category",
        "ai_confidence",
        "created_at",
    )
    list_filter = ("status", "declared_category")
    search_fields = ("user__username", "user__email", "cell_id")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(StackReport)
class StackReportAdmin(admin.ModelAdmin):
    list_display = ("id", "complaint", "user", "created_at")
    list_filter = ("complaint",)
    search_fields = ("complaint__id", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(ComplaintImportanceVote)
class ComplaintImportanceVoteAdmin(admin.ModelAdmin):
    list_display = ("complaint", "user", "importance", "weight", "updated_at")
    list_filter = ("importance",)
    search_fields = ("complaint__id", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
