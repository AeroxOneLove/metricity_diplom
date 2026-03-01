from django.db import models
from core.apps.complaints.models import IncomingReport
from django.contrib.auth import get_user_model

User = get_user_model()

class Decision(models.TextChoices):
    APPROVE = "APPROVE", "Одобрить"
    REJECT = "REJECT", "Отклонить"

class ModerationDecision(models.Model):
    incoming = models.OneToOneField(
        IncomingReport,
        on_delete=models.CASCADE,
        related_name="moderation_decision",
        verbose_name="Входящий отчет",
    )
    moderator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="moderation_decisions",
        verbose_name="Модератор",
    )
    decision = models.CharField(
        max_length=16,
        choices=Decision.choices,
        verbose_name="Решение",
    )
    note = models.TextField(blank=True, verbose_name="Примечание") 
    timestamps = models.DateTimeField(auto_now_add=True, verbose_name="Дата решения")
    
    class Meta:
        verbose_name = "Решение модерации"
        verbose_name_plural = "Решения модерации"

    def __str__(self) -> str:
        return f"Решение модерации<{self.incoming_id}, {self.moderator_id}, {self.decision}>"
    