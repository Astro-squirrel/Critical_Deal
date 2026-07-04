from django.contrib import admin

from .models import DiscountEvent, EpicFreeGame, Price, PriceHistory, Store

admin.site.register(Store)
admin.site.register(Price)
admin.site.register(PriceHistory)
admin.site.register(DiscountEvent)
admin.site.register(EpicFreeGame)

