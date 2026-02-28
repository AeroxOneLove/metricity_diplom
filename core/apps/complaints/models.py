from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class Category(models.TextChoices):
    TRASH = "TRASH", "Trash"
    ROAD = "ROAD", "Road damage"
    LIGHT = "LIGHT", "Lighting"
    GRAFFITI = "GRAFFITI", "Graffiti"
    SNOW = "SNOW", "Snow removal"


class ComplaintStatus(models.TextChoices):
    PUBLISHED = "PUBLISHED", "Published"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"


class IncomingStatus(models.TextChoices):
    PENDING_AI = "PENDING_AI", "Pending AI"
    NEEDS_MODERATION = "NEEDS_MODERATION", "Needs moderation"
    PROCESSED = "PROCESSED", "Processed"
    REJECTED = "REJECTED", "Rejected"


class Complaint(models.Model):
    category = models.CharField(max_length=32, choices=Category.choices)
    status = models.CharField(
        max_length=32,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.PUBLISHED,
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lon = models.DecimalField(max_digits=9, decimal_places=6)
    cell_id = models.CharField(max_length=64, db_index=True)
    stack_count = models.PositiveIntegerField(default=1)
    priority_score = models.FloatField(default=0)
    ai_verified = models.BooleanField(default=False)
    ai_confidence = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["cell_id"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["lat", "lon"]),
        ]
        ordering = ["-priority_score", "-stack_count", "-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Complaint<{self.id}, {self.category}, {self.status}>"


class IncomingReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="incoming_reports")
    declared_category = models.CharField(max_length=32, choices=Category.choices)
    text = models.TextField(blank=True)
    photo = models.ImageField(upload_to="incoming/photos/", blank=True, null=True)

    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lon = models.DecimalField(max_digits=9, decimal_places=6)
    cell_id = models.CharField(max_length=64, db_index=True)

    status = models.CharField(
        max_length=32,
        choices=IncomingStatus.choices,
        default=IncomingStatus.PENDING_AI,
    )
    ai_pred_category = models.CharField(max_length=32, choices=Category.choices, blank=True, null=True)
    ai_confidence = models.FloatField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["cell_id"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Incoming<{self.id}, {self.declared_category}, {self.status}>"


class StackReport(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="stack_reports")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stack_reports")
    text = models.TextField(blank=True)
    photo = models.ImageField(upload_to="stack/photos/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["complaint", "user"], name="unique_complaint_user_stack"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Stack<{self.complaint_id}, user={self.user_id}>"
