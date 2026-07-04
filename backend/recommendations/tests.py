from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserGame
from games.models import Game, GameTag, Genre, Tag
from prices.models import Price, Store
from recommendations.services import (
    _apply_llm_adjustments,
    _chat_context,
    _is_bad_chat_reply,
    calculate_personalized_score,
)


class ChatContextTests(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="Steam", code="steam")

    def test_discount_recommendation_is_not_similar_intent(self):
        self._game("Hotline Miami", "hotline-miami", ["액션", "인디"], ["액션"], 1100, 11000, 90, 85, 100000)
        self._game("BioShock Infinite", "bioshock-infinite", ["액션"], ["풍부한 스토리"], 8000, 32000, 75, 88, 120000)

        context = _chat_context("할인중인 게임 추천해줘", None)

        self.assertTrue(context["intent"]["recommendation"])
        self.assertFalse(context["intent"]["similar_discounted"])
        self.assertGreaterEqual(len(context["matched_games"]), 1)

    def test_similar_discount_uses_reference_even_when_reference_is_not_discounted(self):
        self._game(
            "Stardew Valley",
            "stardew-valley",
            ["시뮬레이션", "RPG", "인디", "캐주얼"],
            ["농장 시뮬레이션", "RPG", "캐주얼"],
            16000,
            16000,
            0,
            98,
            800000,
        )
        self._game(
            "데이브 더 다이버",
            "dave-the-diver",
            ["어드벤처", "캐주얼"],
            ["캐주얼", "RPG", "탐험"],
            12000,
            24000,
            50,
            95,
            120000,
        )

        context = _chat_context("스타듀밸리 같은 할인 게임 추천해줘", None)

        self.assertEqual(context["matched_games"][0]["title"], "Stardew Valley")
        self.assertIn("데이브 더 다이버", [game["title"] for game in context["similar_discounted_games"]])

    def test_unavailable_bioshock_reply_is_rejected(self):
        context = {
            "matched_games": [{"title": "Stardew Valley"}],
            "similar_discounted_games": [{"title": "데이브 더 다이버"}],
        }

        self.assertTrue(_is_bad_chat_reply("무조건 바이오쇼크: 인피니트를 추천합니다.", context))

    def test_excluded_game_is_removed_from_story_recommendations(self):
        self._game("BioShock Infinite", "bioshock-infinite", ["액션"], ["풍부한 스토리"], 8000, 32000, 75, 88, 120000)
        self._game(
            "The Witcher 2: Assassins of Kings Enhanced Edition",
            "witcher-2",
            ["RPG"],
            ["풍부한 스토리", "선택의 중요성"],
            3150,
            21000,
            85,
            88,
            100000,
        )

        context = _chat_context("바이오쇼크 말고 스토리 좋은 게임 추천해줘", None)

        self.assertNotIn("BioShock Infinite", [game["title"] for game in context["matched_games"]])
        self.assertIn("The Witcher 2: Assassins of Kings Enhanced Edition", [game["title"] for game in context["matched_games"]])

    def test_prior_bioshock_history_does_not_drive_new_taste_request(self):
        self._game("BioShock Infinite", "bioshock-infinite", ["액션"], ["풍부한 스토리"], 8000, 32000, 75, 88, 120000)
        self._game("Shadow Warrior", "shadow-warrior", ["액션", "어드벤처"], ["슈팅"], 3200, 32000, 90, 83, 90000)
        history = [{"role": "user", "text": "바이오쇼크 인피니트와 비슷한 할인 게임 추천해줘"}]

        context = _chat_context("내가 할 만한 현재 할인 게임 추천해줘", None, history)

        self.assertFalse(context["intent"]["similar_discounted"])
        self.assertFalse(context["similar_discounted_games"])

    def test_prior_bioshock_history_does_not_override_owned_game_request(self):
        self._game("BioShock Infinite", "bioshock-infinite", ["액션"], ["풍부한 스토리"], 8000, 32000, 75, 88, 120000)
        history = [{"role": "user", "text": "바이오쇼크 인피니트와 비슷한 할인 게임 추천해줘"}]

        context = _chat_context("내가 한 게임 기반으로 지금 할인 중인 게임 추천해줘", None, history)

        self.assertTrue(context["intent"]["user_taste_discounted"])
        self.assertFalse(context["intent"]["similar_discounted"])
        self.assertFalse(context["similar_discounted_games"])

    def _game(self, title, slug, genres, tags, current, original, discount, review_score, review_count):
        game = Game.objects.create(
            title=title,
            slug=slug,
            steam_app_id=str(abs(hash(slug)) % 1000000),
            steam_review_score=review_score,
            steam_review_count=review_count,
            popularity_score=review_count // 100,
        )
        for genre_name in genres:
            genre, _ = Genre.objects.get_or_create(name=genre_name)
            game.genres.add(genre)
        for index, tag_name in enumerate(tags, start=1):
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            GameTag.objects.create(game=game, tag=tag, rank=index, weight=max(1, 10 - index))
        Price.objects.create(
            game=game,
            store=self.store,
            current_price=Decimal(str(current)),
            original_price=Decimal(str(original)),
            discount_rate=discount,
            currency="KRW",
        )
        return game


class PersonalizedScoringRulesTests(TestCase):
    def setUp(self):
        self.store = Store.objects.create(name="Steam", code="steam")
        self.user = get_user_model().objects.create_user(username="scoring-user", password="pass")

    def test_paid_game_uses_price_taste_quality_weights(self):
        game = self._game("Discount Shooter", "discount-shooter", ["Action"], ["Shooter"], 5000, 25000, 80, 90, 8000)

        analysis = calculate_personalized_score(game, self.user)

        self.assertEqual(analysis["metrics"]["scoring"]["mode"], "PURCHASE_TIMING")
        self.assertEqual(analysis["metrics"]["scoring"]["weights"], {"price": 50, "taste": 40, "quality": 10})
        self.assertFalse(analysis["metrics"]["scoring"]["price_score_forced"])
        self.assertEqual(
            analysis["score"],
            int(
                (analysis["price_score"] * 0.50)
                + (analysis["taste_score"] * 0.40)
                + (analysis["quality_score"] * 0.10)
            ),
        )

    def test_free_to_play_game_forces_price_score(self):
        game = self._game("Free Arena", "free-arena", ["Action"], ["Multiplayer"], 0, 0, 0, 84, 3000)

        analysis = calculate_personalized_score(game, self.user)

        self.assertEqual(analysis["pattern_label"], "FREE_TO_PLAY")
        self.assertEqual(analysis["price_score"], 100)
        self.assertEqual(analysis["metrics"]["scoring"]["mode"], "FREE_TO_PLAY")
        self.assertEqual(analysis["metrics"]["scoring"]["weights"], {"taste": 65, "quality": 35})
        self.assertEqual(
            analysis["score"],
            int((analysis["taste_score"] * 0.65) + (analysis["quality_score"] * 0.35)),
        )

    def test_owned_unplayed_game_uses_owned_backlog_mode(self):
        game = self._game("Owned Tactics", "owned-tactics", ["Strategy"], ["Tactical"], 9000, 30000, 70, 92, 10000)
        UserGame.objects.create(user=self.user, game=game, playtime_minutes=0)

        analysis = calculate_personalized_score(game, self.user)

        self.assertTrue(analysis["ownership_context"]["is_owned"])
        self.assertEqual(analysis["ownership_context"]["playtime_segment"], "UNPLAYED")
        self.assertEqual(analysis["price_score"], 100)
        self.assertEqual(analysis["metrics"]["scoring"]["mode"], "OWNED_UNPLAYED")
        self.assertEqual(analysis["metrics"]["scoring"]["weights"], {"taste": 55, "quality": 45})
        self.assertEqual(
            analysis["score"],
            int((analysis["taste_score"] * 0.55) + (analysis["quality_score"] * 0.45)),
        )

    def test_llm_adjustment_cannot_override_owned_scoring_rules(self):
        game = self._game("Owned Tactics LLM", "owned-tactics-llm", ["Strategy"], ["Tactical"], 9000, 30000, 70, 92, 10000)
        UserGame.objects.create(user=self.user, game=game, playtime_minutes=0)
        analysis = calculate_personalized_score(game, self.user)

        adjusted = _apply_llm_adjustments(
            analysis,
            {
                "final_score": 5,
                "decision": "WAIT",
                "price_score": 10,
                "taste_score": 80,
                "quality_score": 90,
                "pattern_label": "NORMAL",
            },
        )

        self.assertEqual(adjusted["price_score"], 100)
        self.assertEqual(adjusted["decision"], "CONSIDER")
        self.assertEqual(adjusted["metrics"]["scoring"]["mode"], "OWNED_UNPLAYED")
        self.assertEqual(adjusted["score"], int((80 * 0.55) + (90 * 0.45)))

    def _game(self, title, slug, genres, tags, current, original, discount, review_score, review_count):
        game = Game.objects.create(
            title=title,
            slug=slug,
            steam_app_id=str(abs(hash(slug)) % 1000000),
            steam_review_score=review_score,
            steam_review_count=review_count,
            popularity_score=review_count // 100,
        )
        for genre_name in genres:
            genre, _ = Genre.objects.get_or_create(name=genre_name)
            game.genres.add(genre)
        for index, tag_name in enumerate(tags, start=1):
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            GameTag.objects.create(game=game, tag=tag, rank=index, weight=max(1, 10 - index))
        Price.objects.create(
            game=game,
            store=self.store,
            current_price=Decimal(str(current)),
            original_price=Decimal(str(original)),
            discount_rate=discount,
            currency="KRW",
        )
        return game
