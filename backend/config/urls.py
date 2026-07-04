from django.contrib import admin
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


def health(request):
    return JsonResponse(
        {
            "service": "Critical Deal API",
            "status": "ok",
            "endpoints": {
                "admin": "/admin/",
                "games": "/api/games/",
                "search": "/api/games/search/?q=hollow",
                "popular_deals": "/api/deals/popular/",
                "epic_free_games": "/api/epic/free-games/",
            },
        }
    )


urlpatterns = [
    path("", health),
    path("api/health/", health),
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/games/", include("games.urls")),
    path("api/", include("prices.urls")),
    path("api/recommendations/", include("recommendations.urls")),
    path("api/wishlist/", include("wishlist.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
