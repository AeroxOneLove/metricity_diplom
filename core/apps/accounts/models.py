from django.contrib.auth import get_user_model
from django.db import models


class UserLevel(models.TextChoices):
    NEWBIE = "NEWBIE", "Новичок"
    ACTIVE = "ACTIVE", "Активный"
    TRUSTED = "TRUSTED", "Доверенный"
    MOD = "MOD", "Модератор"


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

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        ordering = ["-rating", "user_id"]
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self) -> str:  
        return f"Профиль:<{self.user}, {self.get_level_display()}>"
