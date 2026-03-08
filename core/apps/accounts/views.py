from __future__ import annotations

from rest_framework import generics, permissions, status
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .serializers import (
    MetricityTokenObtainPairSerializer,
    RegisterSerializer,
    TokenObtainRequestSerializer,
    TokenPairResponseSerializer,
    TokenRefreshRequestSerializer,
    TokenRefreshResponseSerializer,
    TokenVerifyRequestSerializer,
    UserSerializer,
)


@extend_schema_view(
    post=extend_schema(
        tags=["Аутентификация"],
        auth=[],
        summary="Регистрация пользователя",
        description=(
            "Создаёт нового пользователя, автоматически создаёт профиль "
            "и сразу возвращает пару JWT-токенов."
        ),
        request=RegisterSerializer,
        responses={
            201: TokenPairResponseSerializer,
            400: OpenApiResponse(description="Ошибка валидации входных данных."),
        },
        examples=[
            OpenApiExample(
                "Пример регистрации",
                value={
                    "username": "ivan",
                    "email": "ivan@example.com",
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "password": "ComplexPass123",
                    "password_confirm": "ComplexPass123",
                },
                request_only=True,
            ),
        ],
    ),
)
class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    post=extend_schema(
        tags=["Аутентификация"],
        auth=[],
        summary="Получение JWT-токенов",
        description="Возвращает access- и refresh-токены для существующего пользователя.",
        request=TokenObtainRequestSerializer,
        responses={
            200: TokenPairResponseSerializer,
            401: OpenApiResponse(description="Неверный логин или пароль."),
        },
        examples=[
            OpenApiExample(
                "Пример входа",
                value={"username": "ivan", "password": "ComplexPass123"},
                request_only=True,
            ),
        ],
    ),
)
class MetricityTokenObtainPairView(TokenObtainPairView):
    serializer_class = MetricityTokenObtainPairSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["Аутентификация"],
        auth=[],
        summary="Обновление access-токена",
        description="Принимает refresh-токен и возвращает новый access-токен.",
        request=TokenRefreshRequestSerializer,
        responses={
            200: TokenRefreshResponseSerializer,
            401: OpenApiResponse(description="Refresh-токен недействителен или истёк."),
        },
        examples=[
            OpenApiExample(
                "Пример обновления токена",
                value={"refresh": "<refresh_token>"},
                request_only=True,
            ),
        ],
    ),
)
class MetricityTokenRefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


@extend_schema_view(
    post=extend_schema(
        tags=["Аутентификация"],
        auth=[],
        summary="Проверка JWT-токена",
        description="Проверяет токен на валидность и срок действия.",
        request=TokenVerifyRequestSerializer,
        responses={
            200: OpenApiResponse(description="Токен валиден."),
            401: OpenApiResponse(description="Токен недействителен или истёк."),
        },
        examples=[
            OpenApiExample(
                "Пример проверки токена",
                value={"token": "<access_token>"},
                request_only=True,
            ),
        ],
    ),
)
class MetricityTokenVerifyView(TokenVerifyView):
    permission_classes = [permissions.AllowAny]


@extend_schema_view(
    get=extend_schema(
        tags=["Аутентификация"],
        summary="Текущий пользователь",
        description=(
            "Возвращает данные авторизованного пользователя и его профиль. "
            "Требует JWT access-токен в заголовке `Authorization: Bearer <token>`."
        ),
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Требуется валидный JWT access-токен."),
        },
    ),
)
class MeView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
