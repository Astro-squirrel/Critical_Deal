from django.contrib import admin

from .models import GameAIAnalysis, Recommendation, RecommendationAnalysis

admin.site.register(Recommendation)
admin.site.register(RecommendationAnalysis)
admin.site.register(GameAIAnalysis)

