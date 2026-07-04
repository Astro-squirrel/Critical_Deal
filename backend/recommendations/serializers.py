from rest_framework import serializers


class PurchaseRecommendationSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    decision = serializers.CharField()
    pattern_label = serializers.CharField()
    explanation = serializers.CharField()
    metrics = serializers.DictField()


class GameAIAnalysisSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    decision = serializers.CharField()
    recommendation_text = serializers.CharField()
    pattern_label = serializers.CharField()
    pattern_analysis = serializers.CharField()
    price_score = serializers.IntegerField(required=False)
    taste_score = serializers.IntegerField(required=False)
    quality_score = serializers.IntegerField(required=False)
    price_reason = serializers.CharField(required=False)
    taste_reason = serializers.CharField(required=False)
    metrics = serializers.DictField()
    generated_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    prompt_version = serializers.CharField()
    source = serializers.CharField()
    personalized = serializers.BooleanField(required=False)

