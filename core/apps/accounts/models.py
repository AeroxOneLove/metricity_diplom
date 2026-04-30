from django.contrib.auth import get_user_model
from django.db import models


class UserLevel(models.TextChoices):
    NEWBIE = "NEWBIE", "Новичок"
    ACTIVE = "ACTIVE", "Активный"
    TRUSTED = "TRUSTED", "Доверенный"
    MODERATOR = "MODERATOR", "Модератор"


ACTIVE_RATING_THRESHOLD = 10
TRUSTED_RATING_THRESHOLD = 50

LEVEL_RANKS = {
    UserLevel.NEWBIE: 0,
    UserLevel.ACTIVE: 1,
    UserLevel.TRUSTED: 2,
    UserLevel.MODERATOR: 3,
}


def level_rank(level: str) -> int:
    return LEVEL_RANKS.get(level, LEVEL_RANKS[UserLevel.NEWBIE])


def level_from_rating(rating: int) -> str:
    if rating >= TRUSTED_RATING_THRESHOLD:
        return UserLevel.TRUSTED
    if rating >= ACTIVE_RATING_THRESHOLD:
        return UserLevel.ACTIVE
    return UserLevel.NEWBIE


def promoted_level_for_rating(current_level: str, rating: int) -> str:
    return level_from_rating(rating)


User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="Пользователь")
    rating = models.IntegerField(default=0, verbose_name="Рейтинг")
    level = models.CharField(
        max_length=16,
        choices=UserLevel.choices,
        default=UserLevel.NEWBIE,
        verbose_name="Уровень",
    )
    is_level_manual = models.BooleanField(default=False, verbose_name="Уровень задан вручную")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        ordering = ["-rating", "user_id"]
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def save(self, *args, **kwargs):
        if not self.is_level_manual:
            self.level = level_from_rating(self.rating)

        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Профиль:<{self.user}, {self.get_level_display()}>"


class UserRatingReason(models.TextChoices):
    AI_APPROVED_REPORT = "AI_APPROVED_REPORT", "Отчёт одобрен ИИ"
    MODERATOR_APPROVED_REPORT = "MODERATOR_APPROVED_REPORT", "Отчёт одобрен модератором"
    MODERATOR_REJECTED_REPORT = "MODERATOR_REJECTED_REPORT", "Отчёт отклонён модератором"
    CONFIRMED_COMPLAINT = "CONFIRMED_COMPLAINT", "Подтверждение жалобы"
    OTHER = "OTHER", "Другое"


class UserRatingEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rating_events", verbose_name="Пользователь")
    delta = models.IntegerField(verbose_name="Изменение рейтинга")
    reason = models.CharField(max_length=64, choices=UserRatingReason.choices, verbose_name="Причина")
    complaint = models.ForeignKey(
        "complaints.Complaint",
        on_delete=models.CASCADE,
        related_name="rating_events",
        blank=True,
        null=True,
        verbose_name="Жалоба",
    )
    incoming_report = models.ForeignKey(
        "complaints.IncomingReport",
        on_delete=models.CASCADE,
        related_name="rating_events",
        blank=True,
        null=True,
        verbose_name="Входящий отчёт",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Событие рейтинга пользователя"
        verbose_name_plural = "События рейтинга пользователей"

    def __str__(self) -> str:
        return f"Рейтинг<{self.user_id}, {self.delta}, {self.reason}>"
