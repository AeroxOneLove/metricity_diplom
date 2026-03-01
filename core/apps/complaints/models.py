from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class Category(models.TextChoices):
    TRASH = "TRASH", "Мусор"
    ROAD = "ROAD", "Повреждение дороги"
    GRAFFITI = "GRAFFITI", "Граффити"


class ComplaintStatus(models.TextChoices):
    PUBLISHED = "PUBLISHED", "Опубликовано"
    IN_PROGRESS = "IN_PROGRESS", "В работе"
    RESOLVED = "RESOLVED", "Решено"
    REJECTED = "REJECTED", "Отклонено"


class IncomingStatus(models.TextChoices):
    PENDING_AI = "PENDING_AI", "Ожидает ИИ"
    NEEDS_MODERATION = "NEEDS_MODERATION", "Нуждается в модерации"
    PROCESSED = "PROCESSED", "Обработано"
    REJECTED = "REJECTED", "Отклонено"


class Complaint(models.Model):
    category = models.CharField(max_length=32, choices=Category.choices, verbose_name="Категория")
    status = models.CharField(
        max_length=32,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.PUBLISHED,
        verbose_name="Статус",
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Широта")
    lon = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Долгота")
    cell_id = models.CharField(max_length=64, db_index=True, verbose_name="ID ячейки")
    stack_count = models.PositiveIntegerField(default=1, verbose_name="Количество в стеке")
    priority_score = models.FloatField(default=0, verbose_name="Приоритетный балл")
    ai_verified = models.BooleanField(default=False, verbose_name="Проверено ИИ")
    ai_confidence = models.FloatField(default=0, verbose_name="Уверенность ИИ")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        indexes = [
            models.Index(fields=["cell_id"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["lat", "lon"]),
        ]
        ordering = ["-priority_score", "-stack_count", "-created_at"]
        verbose_name = "Жалоба"
        verbose_name_plural = "Жалобы"
        

    def __str__(self) -> str: 
        return f"Статус<{self.id}, {self.category}, {self.get_status_display()}>"


class IncomingReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="incoming_reports", verbose_name="Пользователь")
    declared_category = models.CharField(max_length=32, choices=Category.choices, verbose_name="Заявленная категория")
    text = models.TextField(blank=True, verbose_name="Текст")
    photo = models.ImageField(upload_to="incoming/photos/", blank=True, null=True, verbose_name="Фото")

    lat = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Широта")
    lon = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Долгота")
    cell_id = models.CharField(max_length=64, db_index=True, verbose_name="ID ячейки")

    status = models.CharField(
        max_length=32,
        choices=IncomingStatus.choices,
        default=IncomingStatus.PENDING_AI,
        verbose_name="Статус",
    )
    ai_pred_category = models.CharField(max_length=32, choices=Category.choices, blank=True, null=True, verbose_name="Категория ИИ")
    ai_confidence = models.FloatField(blank=True, null=True, verbose_name="Уверенность ИИ")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        indexes = [
            models.Index(fields=["cell_id"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]
        verbose_name = "Входящий отчет"
        verbose_name_plural = "Входящие отчеты"

    def __str__(self) -> str: 
        return f"Отчет<{self.id}, {self.get_declared_category_display()}, {self.get_status_display()}>"


class StackReport(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="stack_reports", verbose_name="Жалоба")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stack_reports", verbose_name="Пользователь")
    text = models.TextField(blank=True, verbose_name="Текст")
    photo = models.ImageField(upload_to="stack/photos/", blank=True, null=True, verbose_name="Фото")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["complaint", "user"], name="unique_complaint_user_stack"),
        ]
        ordering = ["-created_at"]
        verbose_name = "Стек жалоб"
        verbose_name_plural = "Стек жалоб"

    def __str__(self) -> str: 
        return f"Очередь<{self.complaint_id}, пользователь={self.user_id}>"
