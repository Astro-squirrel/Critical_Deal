from django.contrib import admin

from .models import EmailVerificationCode, EmailVerificationToken, UserGame, UserProfile, UserSteamAccount

admin.site.register(EmailVerificationCode)
admin.site.register(EmailVerificationToken)
admin.site.register(UserSteamAccount)
admin.site.register(UserProfile)
admin.site.register(UserGame)

