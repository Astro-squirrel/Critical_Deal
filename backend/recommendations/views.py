from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import fail, ok
from games.serializers import GameCardSerializer
from games.services import sync_itad_deals
from .services import HOME_RECOMMENDATION_WEIGHTS, generate_chat_reply, personalized_games, personalized_home_games


class PersonalizedRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.owned_games.exists():
            sync_itad_deals(limit=12)
        return ok(GameCardSerializer(personalized_games(request.user), many=True).data)


class HomePersonalizedRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = _bounded_limit(request.query_params.get("limit"), default=3, maximum=6)
        recommendations = personalized_home_games(request.user, limit=limit)
        items = []
        for item in recommendations:
            game_data = GameCardSerializer(item["game"]).data
            game_data["recommendation"] = {
                "score": item["score"],
                "taste_score": item["taste_score"],
                "quality_score": item["quality_score"],
                "deal_score": item["deal_score"],
                "matched_genres": item["matched_genres"],
                "matched_tags": item["matched_tags"],
                "reason": item["reason"],
            }
            items.append(game_data)
        return ok(
            {
                "items": items,
                "basis": HOME_RECOMMENDATION_WEIGHTS,
                "profile_ready": bool(request.user.owned_games.exists()),
            }
        )


class ChatView(APIView):
    def post(self, request):
        message = str(request.data.get("message", "")).strip()
        if not message:
            return fail("메시지를 입력해 주세요.")
        history = request.data.get("history") or []
        result = generate_chat_reply(message, request.user, history)
        return ok(result)


def _bounded_limit(value, default=3, maximum=6):
    try:
        limit = int(value or default)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, maximum))
