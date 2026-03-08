from django.urls import path

from .views import (
    MeView,
    MetricityTokenObtainPairView,
    MetricityTokenRefreshView,
    MetricityTokenVerifyView,
    RegisterView,
)


app_name = "accounts"


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", MetricityTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", MetricityTokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", MetricityTokenVerifyView.as_view(), name="token_verify"),
    path("me/", MeView.as_view(), name="me"),
]
