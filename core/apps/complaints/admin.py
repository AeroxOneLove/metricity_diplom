from django.contrib import admin

from .models import Complaint, IncomingReport, StackReport


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "category",
        "status",
        "cell_id",
        "stack_count",
        "priority_score",
        "ai_verified",
        "ai_confidence",
        "created_at",
    )
    list_filter = ("category", "status", "ai_verified")
    search_fields = ("cell_id",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-priority_score", "-stack_count", "-created_at")
    date_hierarchy = "created_at"


@admin.register(IncomingReport)
class IncomingReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "declared_category",
        "status",
        "cell_id",
        "ai_pred_category",
        "ai_confidence",
        "created_at",
    )
    list_filter = ("declared_category", "status")
    search_fields = ("user__username", "user__email", "cell_id")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(StackReport)
class StackReportAdmin(admin.ModelAdmin):
    list_display = ("id", "complaint", "user", "created_at")
    list_filter = ("complaint",)
    search_fields = ("complaint__id", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
