from django.urls import path

from .views import (
    AccountDeleteView,
    AccountPasswordChangeView,
    AccountProfileUpdateView,
    CsrfTokenView,
    EmailCodeSendView,
    EmailCodeVerifyView,
    EmailCheckView,
    EmailVerifyView,
    LoginView,
    LogoutView,
    MeView,
    OwnedGameDetailView,
    OwnedGameView,
    ProfileView,
    SignupView,
    SteamConnectView,
    SteamLoginCallbackView,
    SteamLoginStartView,
    UsernameCheckView,
)


urlpatterns = [
    path("csrf/", CsrfTokenView.as_view()),
    path("email/code/", EmailCodeSendView.as_view()),
    path("email/code/verify/", EmailCodeVerifyView.as_view()),
    path("email/check/", EmailCheckView.as_view()),
    path("email/verify/<uuid:token>/", EmailVerifyView.as_view(), name="email-verify"),
    path("signup/", SignupView.as_view()),
    path("username/check/", UsernameCheckView.as_view()),
    path("login/", LoginView.as_view()),
    path("steam/login/", SteamLoginStartView.as_view()),
    path("steam/login/callback/", SteamLoginCallbackView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("me/delete/", AccountDeleteView.as_view()),
    path("me/password/", AccountPasswordChangeView.as_view()),
    path("me/profile/", AccountProfileUpdateView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("owned-games/", OwnedGameView.as_view()),
    path("owned-games/<int:pk>/", OwnedGameDetailView.as_view()),
    path("steam/connect/", SteamConnectView.as_view()),
]

