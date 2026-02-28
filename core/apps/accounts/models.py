from django.contrib.auth import get_user_model
from django.db import models


class UserLevel(models.TextChoices):
    NEWBIE = "NEWBIE", "Новичок"
    ACTIVE = "ACTIVE", "Активный"
    TRUSTED = "TRUSTED", "Доверенный"
    MOD = "MOD", "Модератор"


User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    rating = models.IntegerField(default=0)
    level = models.CharField(
        max_length=16,
        choices=UserLevel.choices,
        default=UserLevel.NEWBIE,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-rating", "user_id"]

    def __str__(self) -> str:  
        return f"Profile<{self.user_id}, {self.level}>"
