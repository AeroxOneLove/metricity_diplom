from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserProfile


User = get_user_model()


@extend_schema_serializer(component_name="ПрофильПользователя")
class UserProfileSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(
        read_only=True,
        label="Рейтинг",
        help_text="Текущий рейтинг пользователя.",
    )
    level = serializers.ChoiceField(
        choices=UserProfile._meta.get_field("level").choices,
        read_only=True,
        label="Уровень",
        help_text="Текущий уровень пользователя: NEWBIE, ACTIVE, TRUSTED или MODERATOR.",
    )
    is_level_manual = serializers.BooleanField(
        read_only=True,
        label="Ручной уровень",
        help_text="Если `true`, уровень назначен вручную и не пересчитывается автоматически по рейтингу.",
    )
    created_at = serializers.DateTimeField(
        read_only=True,
        label="Создан",
        help_text="Дата и время создания профиля.",
    )
    updated_at = serializers.DateTimeField(
        read_only=True,
        label="Обновлён",
        help_text="Дата и время последнего обновления профиля.",
    )

    class Meta:
        model = UserProfile
        fields = ("rating", "level", "is_level_manual", "created_at", "updated_at")
        read_only_fields = fields


@extend_schema_serializer(component_name="Пользователь")
class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, label="ID", help_text="Уникальный идентификатор пользователя.")
    username = serializers.CharField(read_only=True, label="Имя пользователя", help_text="Логин пользователя.")
    email = serializers.EmailField(read_only=True, label="Email", help_text="Адрес электронной почты.")
    first_name = serializers.CharField(read_only=True, label="Имя", help_text="Имя пользователя.")
    last_name = serializers.CharField(read_only=True, label="Фамилия", help_text="Фамилия пользователя.")
    profile = UserProfileSerializer(
        read_only=True,
        label="Профиль",
        help_text="Профиль пользователя с рейтингом и уровнем доступа.",
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "profile")
        read_only_fields = ("id", "profile")


@extend_schema_serializer(component_name="РегистрацияПользователя")
class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        label="Имя пользователя",
        help_text="Уникальный логин для входа в систему.",
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        label="Email",
        help_text="Контактный email. Поле необязательное.",
    )
    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        label="Имя",
        help_text="Имя пользователя. Поле необязательное.",
    )
    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        label="Фамилия",
        help_text="Фамилия пользователя. Поле необязательное.",
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        label="Пароль",
        help_text="Пароль должен соответствовать правилам Django: быть достаточно сложным и не слишком коротким.",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        label="Подтверждение пароля",
        help_text="Повторите пароль для подтверждения.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password", "password_confirm")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
        candidate_user = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class MetricityTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        return super().get_token(user)

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


@extend_schema_serializer(component_name="ЗапросПолученияJWT")
class TokenObtainRequestSerializer(serializers.Serializer):
    username = serializers.CharField(
        label="Имя пользователя",
        help_text="Логин пользователя, для которого нужно получить JWT-токены.",
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        label="Пароль",
        help_text="Пароль пользователя.",
    )


@extend_schema_serializer(component_name="ОтветСJWT")
class TokenPairResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        read_only=True,
        label="Refresh-токен",
        help_text="JWT refresh-токен для обновления access-токена.",
    )
    access = serializers.CharField(
        read_only=True,
        label="Access-токен",
        help_text="JWT access-токен для доступа к защищённым endpoint'ам.",
    )
    user = UserSerializer(
        read_only=True,
        label="Пользователь",
        help_text="Данные пользователя, для которого выданы токены.",
    )


@extend_schema_serializer(component_name="ЗапросОбновленияJWT")
class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        label="Refresh-токен",
        help_text="Действующий refresh-токен, по которому будет выдан новый access-токен.",
    )


@extend_schema_serializer(component_name="ОтветОбновленияJWT")
class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField(
        read_only=True,
        label="Access-токен",
        help_text="Новый access-токен.",
    )


@extend_schema_serializer(component_name="ЗапросПроверкиJWT")
class TokenVerifyRequestSerializer(serializers.Serializer):
    token = serializers.CharField(
        label="Токен",
        help_text="JWT-токен, который нужно проверить на валидность.",
    )
