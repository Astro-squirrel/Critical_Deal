import hashlib
import http.client
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Max, Min, Q
from django.utils import timezone

from games.models import Game
from prices.models import DiscountEvent, PriceHistory
from .models import GameAIAnalysis, UserGameAIAnalysis


AI_ANALYSIS_PROMPT_VERSION = "purchase-v5-price-only"
PERSONALIZED_ANALYSIS_PROMPT_VERSION = "personalized-v15-price-only"
AI_ANALYSIS_TTL_DAYS = 7
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "90"))
PERSONALIZED_LLM_TIMEOUT_SECONDS = int(os.getenv("PERSONALIZED_LLM_TIMEOUT_SECONDS", "30"))
CHAT_LLM_TIMEOUT_SECONDS = int(os.getenv("CHAT_LLM_TIMEOUT_SECONDS", "30"))
DEFAULT_LLM_BASE_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-5.4-nano"
DEFAULT_CHAT_LLM_MODEL = "gpt-5.4-mini"
CHAT_HISTORY_LIMIT = 8
CHAT_RECOMMENDATION_LIMIT = 5
CHAT_CONTEXT_CANDIDATE_LIMIT = 80
CHAT_MIN_QUALITY_REVIEW_COUNT = 100
CHAT_GAME_ALIASES = {
    "다크소울3": {
        "terms": ["dark souls iii", "dark souls 3", "dark souls"],
        "title_hints": ["dark souls", "iii"],
    },
    "다크소울iii": {
        "terms": ["dark souls iii", "dark souls 3", "dark souls"],
        "title_hints": ["dark souls", "iii"],
    },
    "다크소울2": {
        "terms": ["dark souls ii", "dark souls 2", "dark souls"],
        "title_hints": ["dark souls", "ii"],
    },
    "다크소울": {
        "terms": ["dark souls"],
        "title_hints": ["dark souls"],
    },
    "엘든링": {
        "terms": ["elden ring"],
        "title_hints": ["elden ring"],
    },
    "엘든 링": {
        "terms": ["elden ring"],
        "title_hints": ["elden ring"],
    },
    "스타듀밸리": {
        "terms": ["stardew valley"],
        "title_hints": ["stardew valley"],
        "genre_hints": ["시뮬레이션", "RPG", "인디", "캐주얼"],
        "avoid_genres": ["액션", "어드벤처", "레이싱", "스포츠"],
    },
    "스타듀 밸리": {
        "terms": ["stardew valley"],
        "title_hints": ["stardew valley"],
        "genre_hints": ["시뮬레이션", "RPG", "인디", "캐주얼"],
        "avoid_genres": ["액션", "어드벤처", "레이싱", "스포츠"],
    },
    "문명6": {
        "terms": ["civilization", "sid meier"],
        "title_hints": ["civilization® vi", "civilization vi", "civilization 6"],
        "genre_hints": ["전략", "시뮬레이션"],
    },
    "문명": {
        "terms": ["civilization", "sid meier"],
        "title_hints": ["civilization"],
        "genre_hints": ["전략", "시뮬레이션"],
    },
    "바이오쇼크": {
        "terms": ["bioshock", "bio shock"],
        "title_hints": ["bioshock"],
        "genre_hints": ["액션", "어드벤처"],
    },
    "bioshock": {
        "terms": ["bioshock", "bio shock"],
        "title_hints": ["bioshock"],
        "genre_hints": ["액션", "어드벤처"],
    },
    "바숔": {
        "terms": ["bioshock", "bio shock"],
        "title_hints": ["bioshock"],
        "genre_hints": ["액션", "어드벤처"],
    },
    "위쳐": {
        "terms": ["witcher"],
        "title_hints": ["witcher"],
        "genre_hints": ["RPG", "어드벤처"],
    },
    "발더스": {
        "terms": ["baldur"],
        "title_hints": ["baldur"],
        "genre_hints": ["RPG", "전략"],
    },
    "하데스": {
        "terms": ["hades"],
        "title_hints": ["hades"],
        "genre_hints": ["액션", "RPG", "인디"],
    },
    "몬헌": {
        "terms": ["monster hunter"],
        "title_hints": ["monster hunter"],
        "genre_hints": ["액션", "RPG"],
    },
}
CHAT_TAG_ALIASES = {
    "공포": ["공포", "Horror", "서바이벌 호러", "깜놀"],
    "호러": ["공포", "Horror", "서바이벌 호러", "깜놀"],
    "무서운": ["공포", "Horror", "서바이벌 호러"],
    "협동": ["협동", "온라인 협동", "Co-op", "Online Co-Op"],
    "멀티": ["멀티플레이어", "Multiplayer", "협동", "온라인 협동"],
    "멀티플레이": ["멀티플레이어", "Multiplayer", "협동", "온라인 협동"],
    "스토리": ["풍부한 스토리", "Story Rich", "깊은 세계관"],
    "서사": ["풍부한 스토리", "Story Rich", "깊은 세계관"],
    "오픈월드": ["오픈 월드", "Open World", "탐험"],
    "오픈 월드": ["오픈 월드", "Open World", "탐험"],
    "로그라이크": ["Roguelike", "로그라이크", "Roguelite", "로그라이트"],
    "로그라이트": ["Roguelite", "로그라이트", "Roguelike"],
    "소울라이크": ["소울라이크", "고난이도", "Difficult"],
    "어려운": ["고난이도", "Difficult", "소울라이크"],
    "턴제": ["턴제", "턴제 전투", "전략 RPG"],
    "전략": ["전략", "Strategy", "4X"],
    "경영": ["경영", "경제", "건설", "기지 건설"],
    "건설": ["건설", "도시 건설", "기지 건설"],
    "생존": ["생존", "Survival", "제작"],
    "퍼즐": ["퍼즐", "Puzzle", "Logic"],
    "fps": ["1인칭 슈팅", "FPS", "First-Person", "슈팅"],
    "슈팅": ["슈팅", "1인칭 슈팅", "3인칭 슈팅"],
    "덱빌딩": ["덱빌딩", "카드 게임", "카드 배틀"],
}
CHAT_GENRE_ALIASES = {
    "rpg": ["RPG"],
    "알피지": ["RPG"],
    "액션": ["액션"],
    "어드벤처": ["어드벤처"],
    "모험": ["어드벤처"],
    "시뮬레이션": ["시뮬레이션"],
    "시뮬": ["시뮬레이션"],
    "전략": ["전략"],
    "인디": ["인디"],
    "캐주얼": ["캐주얼"],
    "스포츠": ["스포츠"],
    "레이싱": ["레이싱"],
}
PURCHASE_PATTERN_LABELS = {
    "HISTORICAL_LOW",
    "SHORT_CYCLE_WAIT",
    "DEEP_DISCOUNT",
    "NORMAL",
    "NO_PRICE",
    "FREE_TO_PLAY",
}
HOME_RECOMMENDATION_WEIGHTS = {
    "taste": 55,
    "quality": 25,
    "deal": 20,
}


def _decision(score):
    if score >= 85:
        return "BUY"
    if score >= 60:
        return "CONSIDER"
    return "WAIT"


def _decimal_amount(value):
    try:
        return Decimal(str(value or 0))
    except (TypeError, ValueError):
        return Decimal("0")


def _is_free_to_play_price(price):
    if not price:
        return False
    return (
        _decimal_amount(price.current_price) <= 0
        and _decimal_amount(price.original_price) <= 0
        and int(price.discount_rate or 0) == 0
    )


def build_price_features(game):
    analysis = analyze_purchase(game)
    metrics = analysis.get("metrics", {})
    return {
        "score": analysis["score"],
        "decision": analysis["decision"],
        "pattern_label": analysis["pattern_label"],
        "explanation": analysis["explanation"],
        "metrics": {key: _json_safe(value) for key, value in metrics.items()},
    }


def build_user_taste_profile(user):
    owned = list(
        user.owned_games.select_related("game")
        .prefetch_related("game__genres", "game__game_tags__tag")
        .order_by("-playtime_minutes", "game__title")
    )
    genre_weights = {}
    tag_weights = {}
    played_games = []
    total_weight = 0
    total_tag_weight = 0
    for item in owned:
        weight = max(1, item.playtime_minutes // 60)
        total_weight += weight
        game_tags = _game_tag_items(item.game, limit=8)
        played_games.append(
            {
                "game_id": item.game_id,
                "title": item.game.title,
                "playtime_hours": round(item.playtime_minutes / 60, 1),
                "genres": [genre.name for genre in item.game.genres.all()],
                "tags": [tag["name"] for tag in game_tags],
            }
        )
        for genre in item.game.genres.all():
            genre_weights[genre.name] = genre_weights.get(genre.name, 0) + weight
        for game_tag in game_tags:
            tag_weight = weight * max(1, int(game_tag.get("weight") or 1))
            tag_weights[game_tag["name"]] = tag_weights.get(game_tag["name"], 0) + tag_weight
            total_tag_weight += tag_weight

    top_genres = [
        {"name": name, "weight": round(weight / total_weight, 3) if total_weight else 0}
        for name, weight in sorted(genre_weights.items(), key=lambda item: item[1], reverse=True)[:6]
    ]
    top_tags = [
        {"name": name, "weight": round(weight / total_tag_weight, 3) if total_tag_weight else 0}
        for name, weight in sorted(tag_weights.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    return {
        "owned_count": len(owned),
        "top_genres": top_genres,
        "top_tags": top_tags,
        "top_played_games": played_games[:8],
        "library_synced_at": _latest_library_sync(user),
    }


def ensure_personalized_metadata(game, user, limit=8):
    from games.services import enrich_steam_metadata

    candidates = []
    if game.steam_app_id and not game.genres.exists():
        candidates.append(game)

    top_owned_games = (
        user.owned_games.select_related("game")
        .prefetch_related("game__genres", "game__game_tags__tag")
        .order_by("-playtime_minutes", "game__title")[:limit]
    )
    for item in top_owned_games:
        owned_game = item.game
        if owned_game.steam_app_id and not owned_game.genres.exists():
            candidates.append(owned_game)

    unique_games = list({candidate.id: candidate for candidate in candidates}.values())
    if unique_games:
        enrich_steam_metadata(unique_games)


def calculate_taste_score(game, profile):
    top_genres = {item["name"]: item["weight"] for item in profile.get("top_genres", [])}
    top_tags = {item["name"]: item["weight"] for item in profile.get("top_tags", [])}
    if not top_genres and not top_tags:
        return 50, [], []
    game_genres = list(game.genres.all())
    game_tags = _game_tag_items(game)
    if not game_genres and not game_tags:
        return 50, [], []

    matched_genres = []
    for genre in game_genres:
        weight = top_genres.get(genre.name)
        if weight:
            matched_genres.append({"name": genre.name, "weight": weight})

    matched_tags = []
    for tag in game_tags:
        weight = top_tags.get(tag["name"])
        if weight:
            matched_tags.append({"name": tag["name"], "weight": weight, "rank": tag.get("rank")})

    if not matched_genres and not matched_tags:
        return 35, [], []

    genre_weight = min(1, sum(item["weight"] for item in matched_genres))
    tag_weight = min(1, sum(item["weight"] for item in matched_tags))
    strongest_weight = max([item["weight"] for item in matched_genres + matched_tags] or [0])
    coverage_parts = []
    if game_genres:
        coverage_parts.append(len(matched_genres) / max(1, len(game_genres)))
    if game_tags:
        coverage_parts.append(len(matched_tags) / max(1, len(game_tags)))
    taste_coverage = sum(coverage_parts) / len(coverage_parts) if coverage_parts else 0
    owned_count = int(profile.get("owned_count") or 0)

    score = 30
    score += int((genre_weight**0.7) * 22)
    score += int((tag_weight**0.7) * 33)
    score += int(strongest_weight * 14)
    score += int(taste_coverage * 10)
    score += min(8, owned_count // 2)

    if len(matched_genres) + len(matched_tags) == 1:
        score = min(score, 90)
    if genre_weight + tag_weight < 0.65:
        score = min(score, 88)
    return (
        max(0, min(100, score)),
        sorted(matched_genres, key=lambda item: item["weight"], reverse=True),
        sorted(matched_tags, key=lambda item: item["weight"], reverse=True),
    )


def calculate_quality_score(game):
    review_score = int(game.steam_review_score or 0)
    review_count = int(game.steam_review_count or 0)
    if not review_score or not review_count:
        return 50
    confidence = min(1, review_count / 1000)
    return max(0, min(100, int((review_score * 0.75) + (confidence * 25))))


def calculate_personalized_score(game, user):
    ensure_personalized_metadata(game, user)
    price = build_price_features(game)
    profile = build_user_taste_profile(user)
    ownership_context = _target_ownership_context(game, user)
    taste_score, matched_genres, matched_tags = calculate_taste_score(game, profile)
    quality_score = calculate_quality_score(game)
    price_score = _personalized_price_score(price, ownership_context)
    final_score, scoring_context = _personalized_final_score(
        price_score=price_score,
        taste_score=taste_score,
        quality_score=quality_score,
        pattern_label=price["pattern_label"],
        ownership_context=ownership_context,
    )
    return {
        "score": final_score,
        "decision": _decision(final_score),
        "price_score": price_score,
        "taste_score": taste_score,
        "quality_score": quality_score,
        "pattern_label": price["pattern_label"],
        "price_features": price,
        "taste_profile": profile,
        "matched_genres": matched_genres,
        "matched_tags": matched_tags,
        "ownership_context": ownership_context,
        "metrics": {
            "price": price["metrics"],
            "taste": {
                "owned_count": profile["owned_count"],
                "top_genres": profile["top_genres"],
                "top_tags": profile["top_tags"],
                "matched_genres": matched_genres,
                "matched_tags": matched_tags,
            },
            "quality": {
                "steam_review_score": game.steam_review_score,
                "steam_review_count": game.steam_review_count,
            },
            "ownership": ownership_context,
            "scoring": scoring_context,
        },
    }


def analyze_purchase(game):
    prices = list(game.prices.select_related("store").order_by("current_price"))
    if not prices:
        return {
            "score": 50,
            "decision": "WAIT",
            "pattern_label": "NO_PRICE",
            "explanation": "가격 데이터가 부족해 구매 시점을 판단하기 어렵습니다. 가격 정보가 갱신된 뒤 다시 확인해 주세요.",
            "metrics": {},
        }

    best = prices[0]
    if _is_free_to_play_price(best):
        return _free_to_play_analysis(game, best)

    low = best.historical_low_price or best.current_price
    current_vs_low = (best.current_price / low * Decimal("100")).quantize(Decimal("0.01")) if low else Decimal("100")
    current_vs_low_text = _relative_low_price_text(current_vs_low)
    history = list(PriceHistory.objects.filter(game=game, store=best.store).order_by("recorded_at"))
    discounted = [item for item in history if item.discount_rate > 0]
    today = timezone.localdate()
    last_discount = discounted[-1].recorded_at if discounted else today
    days_since_last = (today - last_discount).days
    intervals = [(discounted[i].recorded_at - discounted[i - 1].recorded_at).days for i in range(1, len(discounted))]
    avg_interval = int(sum(intervals) / len(intervals)) if intervals else 60
    frequency = len(discounted)
    platform_rank = 1

    score = 35
    if best.current_price <= low:
        score += 30
    elif current_vs_low <= 110:
        score += 22
    elif current_vs_low <= 130:
        score += 12
    score += min(best.discount_rate, 60) // 2
    if days_since_last <= 30 and best.discount_rate < 20:
        score -= 12
    if avg_interval <= 45 and best.discount_rate < 25:
        score -= 10
    if len(prices) > 1 and best.current_price == min(p.current_price for p in prices):
        score += 5
    score = max(0, min(100, int(score)))

    decision = _decision(score)
    if best.current_price <= low:
        pattern = "HISTORICAL_LOW"
    elif avg_interval <= 45 and best.discount_rate < 25:
        pattern = "SHORT_CYCLE_WAIT"
    elif best.discount_rate >= 40:
        pattern = "DEEP_DISCOUNT"
    else:
        pattern = "NORMAL"

    explanation = (
        f"현재 최저가는 {best.store.name} 기준 {best.current_price:,.0f}원이고, "
        f"역대 최저가 {low:,.0f}원과 비교하면 {current_vs_low_text}. "
        f"현재 할인율은 {best.discount_rate}%이고, 최근 할인 이후 {days_since_last}일이 지났습니다. "
        f"평균 할인 간격은 약 {avg_interval}일로 계산되어 현재 조건은 {decision} 판단에 가깝습니다."
    )
    pattern_explanation = _discount_pattern_text(
        frequency=frequency,
        avg_interval=avg_interval,
        days_since_last=days_since_last,
        current_discount=best.discount_rate,
    )
    return {
        "score": score,
        "decision": decision,
        "pattern_label": pattern,
        "explanation": explanation,
        "metrics": {
            "current_vs_low_percent": current_vs_low,
            "current_vs_low_text": current_vs_low_text,
            "days_since_last_discount": days_since_last,
            "average_discount_interval": avg_interval,
            "discount_frequency": frequency,
            "discount_pattern_text": pattern_explanation,
            "next_discount_forecast": {},
            "next_discount_forecast_text": "",
            "platform_price_rank": platform_rank,
        },
    }


def _free_to_play_analysis(game, price):
    quality_score = calculate_quality_score(game)
    review_count = int(game.steam_review_count or 0)
    score = max(45, min(90, int(45 + (quality_score * 0.45))))
    if review_count < 50:
        score = min(score, 68)

    explanation = (
        f"{price.store.name} 기준 기본 게임은 상시 무료로 보이며, 할인 때문에 일시적으로 무료가 된 상태가 아닙니다. "
        "따라서 역대 최저가나 다음 할인 타이밍을 기다리는 문제보다는 장르/태그 취향, Steam 평가, "
        "멀티플레이 구조와 부분유료화 과금 방식이 맞는지를 중심으로 판단하는 편이 자연스럽습니다."
    )
    pattern_text = (
        "기본 게임 가격은 상시 무료라 할인 주기 분석은 적용하지 않습니다. "
        "DLC, 배틀패스, 스킨, 인게임 재화처럼 플레이 후 결제될 수 있는 요소는 별도로 확인하는 편이 좋습니다."
    )

    return {
        "score": score,
        "decision": _decision(score),
        "pattern_label": "FREE_TO_PLAY",
        "explanation": explanation,
        "metrics": {
            "analysis_mode": "FREE_TO_PLAY",
            "pricing_context": "FREE_TO_PLAY",
            "is_free_to_play": True,
            "is_temporarily_free": False,
            "current_vs_low_percent": Decimal("100.00"),
            "current_vs_low_text": "기본 게임은 상시 무료입니다",
            "days_since_last_discount": 0,
            "average_discount_interval": 0,
            "discount_frequency": 0,
            "discount_pattern_text": pattern_text,
            "next_discount_forecast": {},
            "next_discount_forecast_text": "",
            "platform_price_rank": 1,
            "quality_score": quality_score,
            "monetization_note": "기본 게임은 무료지만 DLC, 배틀패스, 스킨, 인게임 재화 결제가 있을 수 있습니다.",
        },
    }


def _relative_low_price_text(current_vs_low):
    ratio = Decimal(str(current_vs_low)) / Decimal("100")
    if ratio <= Decimal("1.01"):
        return "역대 최저가 수준입니다"
    if ratio < Decimal("1.2"):
        diff_percent = current_vs_low - Decimal("100")
        return f"역대 최저가보다 약 {diff_percent:.0f}% 비싼 수준입니다"
    return f"역대 최저가의 약 {ratio:.1f}배 수준입니다"


def _discount_pattern_text(frequency, avg_interval, days_since_last, current_discount):
    if frequency <= 1:
        return "저장된 할인 이력이 충분하지 않아 반복 패턴을 단정하기 어렵습니다. 현재 할인율과 역대 최저가 근접도를 중심으로 보는 편이 안전합니다."

    if avg_interval <= 45:
        cadence = f"할인이 비교적 자주 반복되는 편입니다. 평균적으로 약 {avg_interval}일 간격으로 할인 기록이 나타났습니다."
    elif avg_interval <= 90:
        cadence = f"할인이 주기적으로 돌아오는 편입니다. 평균 할인 간격은 약 {avg_interval}일입니다."
    else:
        cadence = f"할인 간격이 긴 편입니다. 평균 할인 간격은 약 {avg_interval}일이라 할인 기회가 자주 보이지 않았습니다."

    if current_discount <= 0:
        current = f"현재는 할인 중이 아니고, 마지막 할인 이후 {days_since_last}일이 지났습니다."
    elif days_since_last <= 14:
        current = f"현재 할인은 최근 할인 구간에 속하며 할인율은 {current_discount}%입니다."
    else:
        current = f"마지막 할인 기록 이후 {days_since_last}일이 지났고, 현재 할인율은 {current_discount}%입니다."

    if avg_interval <= 45 and current_discount < 25:
        advice = "반복 할인이 잦은 게임인데 현재 할인율은 강하지 않아 더 큰 할인을 기다릴 여지가 있습니다."
    elif current_discount >= 40:
        advice = "현재 할인율은 이력상 강한 할인 구간으로 볼 수 있습니다."
    else:
        advice = "현재 할인은 일반적인 할인 패턴 안에 있는 수준으로 보입니다."

    return f"{cadence} {current} {advice}"


def _next_discount_forecast(game, store, discounted, today, current_discount):
    event_start_dates = list(
        DiscountEvent.objects.filter(game=game, store=store)
        .order_by("started_at")
        .values_list("started_at", flat=True)
    )
    start_dates = sorted(set(day for day in event_start_dates if day))
    if len(start_dates) < 2:
        start_dates = _compressed_discount_start_dates(item.recorded_at for item in discounted)

    if len(start_dates) < 2:
        return {
            "has_forecast": False,
            "confidence": "low",
            "discount_start_count": len(start_dates),
            "text": "할인 시작 이력이 충분하지 않아 다음 할인 기간은 아직 좁혀 예측하기 어렵습니다.",
        }

    intervals = [(start_dates[i] - start_dates[i - 1]).days for i in range(1, len(start_dates))]
    intervals = [interval for interval in intervals if interval > 0]
    if not intervals:
        return {
            "has_forecast": False,
            "confidence": "low",
            "discount_start_count": len(start_dates),
            "text": "할인 시작 간격이 불규칙해 다음 할인 기간은 아직 좁혀 예측하기 어렵습니다.",
        }

    avg_interval = max(1, int(sum(intervals) / len(intervals)))
    center = start_dates[-1] + timedelta(days=avg_interval)
    while center < today:
        center += timedelta(days=avg_interval)

    padding = max(7, min(30, avg_interval // 5))
    window_start = center - timedelta(days=padding)
    window_end = center + timedelta(days=padding)
    confidence = "high" if len(start_dates) >= 6 and avg_interval <= 120 else "medium" if len(start_dates) >= 3 else "low"
    current_note = "현재 할인 중이므로 이번 할인 이후의 다음 구간까지 보면 " if current_discount > 0 else ""
    text = (
        f"{current_note}이력 기준 다음 할인은 {window_start.isoformat()}부터 "
        f"{window_end.isoformat()} 사이로 예상됩니다. 실제 Steam 세일 일정에 따라 달라질 수 있는 추정입니다."
    )

    return {
        "has_forecast": True,
        "estimated_window_start": window_start,
        "estimated_window_center": center,
        "estimated_window_end": window_end,
        "average_discount_start_interval": avg_interval,
        "discount_start_count": len(start_dates),
        "confidence": confidence,
        "text": text,
    }


def _compressed_discount_start_dates(dates):
    starts = []
    previous = None
    for day in sorted(set(day for day in dates if day)):
        if previous is None or (day - previous).days > 7:
            starts.append(day)
        previous = day
    return starts


def _pattern_analysis_text(pattern_text, forecast):
    return pattern_text


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _game_tag_items(game, limit=12):
    prefetched = getattr(game, "_prefetched_objects_cache", {})
    if "game_tags" in prefetched:
        game_tags = sorted(prefetched["game_tags"], key=lambda item: (item.rank, item.tag.name))
    else:
        game_tags = game.game_tags.select_related("tag").order_by("rank", "tag__name")
    return [
        {"name": game_tag.tag.name, "rank": game_tag.rank, "weight": game_tag.weight}
        for game_tag in list(game_tags[:limit])
    ]


def _latest_library_sync(user):
    latest = user.owned_games.order_by("-synced_at").values_list("synced_at", flat=True).first()
    return latest.isoformat() if latest else None


def _owned_playtime_segment(playtime_minutes):
    minutes = int(playtime_minutes or 0)
    if minutes <= 0:
        return "UNPLAYED"
    hours = minutes / 60
    if hours <= 20:
        return "LIGHTLY_PLAYED"
    if hours <= 100:
        return "MEANINGFULLY_PLAYED"
    return "PROVEN_FAVORITE"


def _owned_playtime_label(playtime_minutes):
    minutes = int(playtime_minutes or 0)
    if minutes <= 0:
        return "0시간"
    hours = minutes / 60
    if hours < 1:
        return f"{minutes}분"
    if hours.is_integer():
        return f"{int(hours)}시간"
    return f"{hours:.1f}시간"


def _target_ownership_context(game, user):
    if not user or not getattr(user, "is_authenticated", False):
        return {"is_owned": False}
    owned = user.owned_games.filter(game=game).first()
    if not owned:
        return {"is_owned": False}
    playtime_minutes = int(owned.playtime_minutes or 0)
    return {
        "is_owned": True,
        "playtime_minutes": playtime_minutes,
        "playtime_hours": round(playtime_minutes / 60, 1),
        "playtime_label": _owned_playtime_label(playtime_minutes),
        "playtime_segment": _owned_playtime_segment(playtime_minutes),
        "synced_at": owned.synced_at.isoformat() if owned.synced_at else None,
    }


def _ownership_analysis_mode(ownership_context, is_free_to_play=False):
    if ownership_context.get("is_owned"):
        return f"OWNED_{ownership_context.get('playtime_segment') or 'UNKNOWN'}"
    return "FREE_TO_PLAY" if is_free_to_play else "PURCHASE_TIMING"


def _personalized_price_score(price, ownership_context):
    if ownership_context.get("is_owned") or price.get("pattern_label") == "FREE_TO_PLAY":
        return 100
    return int(price.get("score") or 0)


def _owned_playtime_context_score(ownership_context):
    segment = ownership_context.get("playtime_segment")
    hours = float(ownership_context.get("playtime_hours") or 0)
    if segment == "UNPLAYED":
        return 50
    if segment == "LIGHTLY_PLAYED":
        return max(45, min(65, int(45 + (hours / 20) * 20)))
    if segment == "MEANINGFULLY_PLAYED":
        return max(65, min(85, int(65 + ((hours - 20) / 80) * 20)))
    if segment == "PROVEN_FAVORITE":
        return 95
    return 50


def _personalized_final_score(price_score, taste_score, quality_score, pattern_label, ownership_context):
    price_score = int(price_score or 0)
    taste_score = int(taste_score or 0)
    quality_score = int(quality_score or 0)

    if ownership_context.get("is_owned"):
        playtime_score = _owned_playtime_context_score(ownership_context)
        segment = ownership_context.get("playtime_segment") or "UNKNOWN"
        if segment == "UNPLAYED":
            weights = {"taste": 55, "quality": 45}
            score = int((taste_score * 0.55) + (quality_score * 0.45))
        elif segment == "PROVEN_FAVORITE":
            weights = {"quality": 30, "playtime": 70}
            score = int((quality_score * 0.30) + (playtime_score * 0.70))
        else:
            weights = {"taste": 45, "quality": 35, "playtime": 20}
            score = int((taste_score * 0.45) + (quality_score * 0.35) + (playtime_score * 0.20))
        return max(0, min(100, score)), {
            "mode": f"OWNED_{segment}",
            "weights": weights,
            "price_score_forced": True,
            "playtime_score": playtime_score,
        }

    if pattern_label == "FREE_TO_PLAY":
        score = int((taste_score * 0.65) + (quality_score * 0.35))
        return max(0, min(100, score)), {
            "mode": "FREE_TO_PLAY",
            "weights": {"taste": 65, "quality": 35},
            "price_score_forced": True,
            "playtime_score": None,
        }

    score = int((price_score * 0.50) + (taste_score * 0.40) + (quality_score * 0.10))
    return max(0, min(100, score)), {
        "mode": "PURCHASE_TIMING",
        "weights": {"price": 50, "taste": 40, "quality": 10},
        "price_score_forced": False,
        "playtime_score": None,
    }


def personalized_fingerprint(game, user):
    ownership_context = _target_ownership_context(game, user)
    payload = {
        "price": price_fingerprint(game),
        "owned_count": user.owned_games.count(),
        "latest_library_sync": _latest_library_sync(user),
        "target_ownership": ownership_context,
        "game_genres": list(game.genres.order_by("name").values_list("name", flat=True)),
        "game_tags": [item["name"] for item in _game_tag_items(game, limit=20)],
        "review_score": game.steam_review_score,
        "review_count": game.steam_review_count,
    }
    raw = json.dumps(payload, sort_keys=True, default=_json_safe)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fallback_personalized_text(game, analysis):
    matched = analysis["matched_genres"]
    matched_tags = analysis.get("matched_tags", [])
    top_match = ", ".join(item["name"] for item in (matched_tags[:3] + matched[:3])[:3])
    top_user_genres = ", ".join(item["name"] for item in analysis["taste_profile"].get("top_genres", [])[:3])
    top_user_tags = ", ".join(item["name"] for item in analysis["taste_profile"].get("top_tags", [])[:4])
    game_genres = ", ".join(genre.name for genre in game.genres.all()[:3])
    game_tags = ", ".join(item["name"] for item in _game_tag_items(game, limit=5))
    price_reason = analysis["price_features"]["explanation"]
    price_metrics = analysis["price_features"]["metrics"]
    is_free_to_play = bool(price_metrics.get("is_free_to_play"))
    pattern_analysis = _pattern_analysis_text(
        price_metrics.get("discount_pattern_text") or price_reason,
        price_metrics.get("next_discount_forecast") or {},
    )
    if is_free_to_play:
        decision_phrase = {
            "BUY": "취향이 맞는다면 부담 없이 시작해볼 만합니다",
            "CONSIDER": "무료라 가격 대기는 불필요하지만, 플레이 성향과 과금 구조를 확인하고 시작하는 편이 좋습니다",
            "WAIT": "무료라도 플레이 성향과는 거리가 있어 우선순위는 낮아 보입니다",
        }.get(analysis["decision"], "플레이 성향과 과금 구조를 조금 더 확인해 보는 편이 좋습니다")
    else:
        decision_phrase = {
            "BUY": "지금 구매 쪽으로 기울어도 좋은 조건입니다",
            "CONSIDER": "관심이 있다면 구매를 고려할 만하지만, 더 큰 할인을 기다릴 여지도 있습니다",
            "WAIT": "지금 가격만 보면 바로 사기보다는 가격 메리트가 더 좋아질 때를 기다리는 편이 좋습니다",
        }.get(analysis["decision"], "현재 조건을 조금 더 확인해 보는 편이 좋습니다")

    taste_reason = _fallback_taste_reason(
        taste_score=analysis["taste_score"],
        matched_genres=matched,
        matched_tags=matched_tags,
        matched_text=top_match,
        top_user_genres=top_user_genres,
        top_user_tags=top_user_tags,
        game_genres=game_genres,
        game_tags=game_tags,
        is_free_to_play=is_free_to_play,
    )

    ownership_context = analysis.get("ownership_context") or {}
    if ownership_context.get("is_owned"):
        return _fallback_owned_personalized_text(
            game=game,
            ownership_context=ownership_context,
            taste_reason=taste_reason,
            price_reason=price_reason,
            pattern_analysis=pattern_analysis,
        )

    if is_free_to_play:
        recommendation_text = f"기본 게임이 상시 무료인 점, 플레이 취향, Steam 평가를 함께 보면 {decision_phrase}."
    else:
        recommendation_text = f"가격 흐름, 플레이 취향, Steam 평가를 함께 보면 {decision_phrase}."

    return {
        "recommendation_text": recommendation_text,
        "price_reason": price_reason,
        "taste_reason": taste_reason,
        "pattern_analysis": pattern_analysis,
    }


def _fallback_owned_personalized_text(game, ownership_context, taste_reason, price_reason, pattern_analysis):
    segment = ownership_context.get("playtime_segment")
    playtime_label = ownership_context.get("playtime_label") or "0시간"
    title = game.title
    owned_price_reason = (
        "이미 라이브러리에 있는 게임이라 본편 구매 가격을 다시 판단하는 것은 큰 의미가 없습니다. "
        "추가로 돈을 쓸 일이 있다면 DLC, 확장팩, 번들 같은 선택 구매만 별도로 확인하는 편이 좋습니다."
    )

    if segment == "UNPLAYED":
        recommendation_text = (
            f"{title}은 이미 라이브러리에 있지만 아직 플레이하지 않으셨군요. "
            "구매 판단보다는 지금 설치해서 시작해볼 만한 백로그인지 보는 게 맞습니다."
        )
        owned_taste_reason = (
            f"플레이시간이 {playtime_label}이라 실제로 취향에 맞았는지는 아직 확인되지 않았습니다. "
            f"{taste_reason}"
        )
        owned_pattern_analysis = (
            "본편 구매 타이밍보다는 백로그 우선순위 관점으로 보는 편이 자연스럽습니다. "
            "취향 접점과 시작 장벽, 현재 관심도를 기준으로 먼저 켜볼 만한지 판단해 주세요."
        )
    elif segment == "LIGHTLY_PLAYED":
        recommendation_text = (
            f"{title}은 약 {playtime_label} 플레이하셨네요. "
            "초반은 경험했지만 깊게 파고든 수준은 아니라, 이어서 할 만한지 다시 판단하는 쪽이 좋습니다."
        )
        owned_taste_reason = (
            f"플레이시간이 {playtime_label}인 점을 보면 취향에 완전히 맞았다고 단정하기는 아직 이릅니다. "
            f"{taste_reason}"
        )
        owned_pattern_analysis = (
            "본편은 이미 보유 중이므로 구매 타이밍보다 중단했던 이유와 다시 이어 할 동기가 더 중요합니다. "
            "짧게 다시 플레이해보고 흐름이 맞는지 확인하는 쪽이 좋습니다."
        )
    elif segment == "MEANINGFULLY_PLAYED":
        recommendation_text = (
            f"{title}은 약 {playtime_label} 플레이하신 게임입니다. "
            "어느 정도 즐긴 기록이 있으니 구매 판단보다는 복귀할 이유가 있는지 보는 게 자연스럽습니다."
        )
        owned_taste_reason = (
            f"{playtime_label} 정도 플레이했다면 기본 플레이는 어느 정도 맞았던 게임으로 볼 수 있습니다. "
            f"{taste_reason}"
        )
        owned_pattern_analysis = (
            "이미 의미 있게 플레이한 게임이라 본편 가격 메리트보다 복귀 가치, 업데이트, DLC나 확장팩 관심도가 더 중요합니다."
        )
    else:
        recommendation_text = (
            f"{title}은 약 {playtime_label} 플레이하신 게임입니다. "
            "이 정도면 이미 취향에 충분히 맞았던 게임으로 보는 게 자연스럽습니다."
        )
        owned_taste_reason = (
            f"{playtime_label} 이상 플레이한 기록이 있으므로 이 게임이 취향에 맞는지는 이미 검증된 편입니다. "
            "본편 취향 분석보다는 다시 복귀할 이유가 있는지, 또는 비슷한 게임을 고를 때 기준점으로 삼는 편이 좋습니다."
        )
        owned_pattern_analysis = (
            "본편 구매 분석은 크게 의미가 적습니다. 지금은 복귀 가치, DLC나 확장팩, 또는 이 게임과 비슷한 추천작을 볼 때 더 유용합니다."
        )

    return {
        "recommendation_text": recommendation_text,
        "price_reason": owned_price_reason,
        "taste_reason": owned_taste_reason,
        "pattern_analysis": owned_pattern_analysis or pattern_analysis or price_reason,
    }


def _fallback_taste_reason(
    taste_score,
    matched_genres,
    matched_tags,
    matched_text,
    top_user_genres,
    top_user_tags,
    game_genres,
    game_tags,
    is_free_to_play=False,
):
    top_user_text = top_user_tags or top_user_genres
    game_text = game_tags or game_genres
    if not top_user_text:
        if game_text:
            focus_sentence = (
                "지금은 Steam 평가와 게임 성향을 함께 보는 편이 좋습니다."
                if is_free_to_play
                else "지금은 가격 흐름과 Steam 평가를 함께 보는 편이 좋습니다."
            )
            return (
                f"아직 플레이 기록이 충분하지 않아 {game_text} 취향과 얼마나 맞을지는 조심스럽게 봐야 합니다. "
                f"{focus_sentence}"
            )
        if is_free_to_play:
            return "아직 플레이 기록이 충분하지 않아 개인 취향보다는 Steam 평가와 게임 성향을 중심으로 봤습니다."
        return "아직 플레이 기록이 충분하지 않아 개인 취향보다는 가격 흐름과 Steam 평가를 중심으로 봤습니다."

    if (matched_genres or matched_tags) and taste_score >= 85:
        return (
            f"플레이 기록에서 강하게 드러난 {matched_text} 취향과 이 게임의 플레이 성향이 잘 맞습니다. "
            "이미 오래 즐겨온 계열과 가까워 실제로 손이 갈 가능성이 높아 보입니다."
        )

    if (matched_genres or matched_tags) and taste_score >= 70:
        final_hint = "과금 구조와 플레이 방식까지 함께 보면 좋습니다." if is_free_to_play else "가격 조건까지 함께 보면 좋습니다."
        return (
            f"선호하는 {matched_text} 성향과 겹치는 지점이 있어 취향 궁합은 좋은 편입니다. "
            f"다만 평소 가장 많이 즐긴 축과 완전히 같지는 않아 {final_hint}"
        )

    if (matched_genres or matched_tags) and taste_score >= 55:
        return (
            f"{matched_text} 쪽 취향과 일부 접점은 있지만, 라이브러리 전체 기준으로는 강한 매칭까지는 아닙니다. "
            "게임의 분위기나 핵심 플레이가 끌린다면 고려할 만한 정도로 보는 게 좋습니다."
        )

    if matched_genres or matched_tags:
        trigger_text = "무료 접근성과 평가가 끌릴 때 시도해볼 만한 쪽입니다" if is_free_to_play else "할인율이나 평가가 끌릴 때 시도해볼 만한 쪽입니다"
        return (
            f"{matched_text} 단서가 일부 겹치지만 플레이 비중이 높았던 취향과는 거리가 있습니다. "
            f"좋아하는 핵심 취향이라기보다는 {trigger_text}."
        )

    if taste_score >= 45:
        genre_hint = f"현재 주요 선호 성향은 {top_user_text} 쪽입니다. "
        game_hint = f"이 게임은 {game_text} 성향이라 " if game_text else ""
        approach_text = "무료로 가볍게 체험해보고 접근하는 편이 좋습니다" if is_free_to_play else "가격 조건을 보고 접근하는 편이 좋습니다"
        return (
            f"{genre_hint}{game_hint}직접 겹치는 성향은 적지만 완전히 벗어난 선택지는 아닙니다. "
            f"새 장르를 시도하고 싶을 때 {approach_text}."
        )

    genre_hint = f"주요 선호 성향인 {top_user_text}와는 " if top_user_text else "보유 라이브러리와는 "
    game_hint = f"이 게임의 {game_text} 성향이 " if game_text else "이 게임의 성향이 "
    reason_to_try = "친구와 함께할 계기나 높은 평가가 있을 때만 가볍게 보는 편이 좋습니다" if is_free_to_play else "강한 할인이나 높은 평가가 있을 때 신중히 보는 게 좋습니다"
    return (
        f"{genre_hint}{game_hint}뚜렷하게 맞물리지는 않습니다. "
        f"평소 취향만 놓고 보면 우선순위는 낮아 보여서 {reason_to_try}."
    )


def _llm_payload(game, analysis):
    price_metrics = analysis["price_features"].get("metrics", {})
    is_free_to_play = bool(price_metrics.get("is_free_to_play"))
    ownership_context = analysis.get("ownership_context") or {"is_owned": False}
    analysis_mode = _ownership_analysis_mode(ownership_context, is_free_to_play)
    price_analysis = {
        **analysis["price_features"],
        "metrics": {
            key: value
            for key, value in price_metrics.items()
            if key not in {"next_discount_forecast", "next_discount_forecast_text"}
        },
    }
    return {
        "game": {
            "title": game.title,
            "genres": [genre.name for genre in game.genres.all()],
            "tags": _game_tag_items(game, limit=12),
            "steam_review_score": game.steam_review_score,
            "steam_review_count": game.steam_review_count,
        },
        "scores": {
            "local_final_score": analysis["score"],
            "local_decision": analysis["decision"],
            "price_score": analysis["price_score"],
            "local_taste_score": analysis["taste_score"],
            "quality_score": analysis["quality_score"],
        },
        "price_analysis": price_analysis,
        "pricing_context": {
            "is_free_to_play": is_free_to_play,
            "is_temporarily_free": bool(price_metrics.get("is_temporarily_free")),
            "analysis_mode": analysis_mode,
            "guidance": (
                "The user already owns the base game. Do not frame the base game as a purchase timing decision. "
                "Use ownership_context.playtime_segment and playtime_label to judge whether to start, continue, revisit, "
                "or treat it as an already proven taste signal. Mention price only for optional DLC, expansions, bundles, "
                "or extra purchases when relevant."
                if ownership_context.get("is_owned")
                else
                "Base game is permanently free-to-play. Do not frame this as a discount, historical-low, "
                "or wait-for-a-better-price decision. Judge whether the user is likely to enjoy trying it, "
                "and mention optional DLC, battle pass, cosmetics, or in-game purchases only as caveats."
                if is_free_to_play
                else "Analyze the current price value only from current price, discount depth, historical low, and past discount cadence. Do not forecast a future discount window."
            ),
        },
        "ownership_context": ownership_context,
        "user_taste": {
            "owned_count": analysis["taste_profile"]["owned_count"],
            "top_genres": analysis["taste_profile"]["top_genres"],
            "top_tags": analysis["taste_profile"].get("top_tags", []),
            "matched_genres": analysis["matched_genres"],
            "matched_tags": analysis.get("matched_tags", []),
            "top_played_games": analysis["taste_profile"]["top_played_games"],
        },
    }


def _generate_personalized_llm_analysis(game, analysis):
    api_key = os.getenv("GMS_KEY", "").strip()
    if not api_key:
        return analysis, _fallback_personalized_text(game, analysis), "fallback"
    base_url = os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL).strip().rstrip("/")
    model = os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip()
    prompt_payload = _llm_payload(game, analysis)
    try:
        content = _post_gms_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=[
                {
                        "role": "system",
                        "content": (
                            "You are the final purchase and free-to-play analysis judge for a Korean game deal service. "
                            "For this test, make the full visible AI purchase analysis yourself using the provided local "
                            "analysis as reference material. Suggest price_score, taste_score, quality_score, "
                            "final_score, decision, pattern_label, and all explanation text, but the service will enforce "
                            "final scoring rules after your JSON is returned. "
                            "Scores must be integers from 0 to 100. Valid decisions are BUY, CONSIDER, WAIT. "
                            "Use BUY for strong buy timing or strong try-now fit in FREE_TO_PLAY mode, CONSIDER for mixed "
                            "or acceptable timing/fit, and WAIT for weak price timing or poor fit. "
                            "Valid pattern_label values are HISTORICAL_LOW, SHORT_CYCLE_WAIT, DEEP_DISCOUNT, NORMAL, NO_PRICE, FREE_TO_PLAY. "
                            "Explain current_vs_low_percent using current_vs_low_text, not raw percentages. "
                            "For price_reason and pattern_analysis, judge only the current price value: current price, "
                            "discount depth, historical-low closeness, and past discount cadence. Do not predict, estimate, "
                            "or mention future discount dates, next discount windows, upcoming sale periods, or phrases like "
                            "'다음 할인은 ... 사이', '다음 세일', '예상 구간', or '할인 예측'. "
                            "If ownership_context.is_owned is true, the user already owns the base game. Do not frame "
                            "the base game as something to buy, skip, or wait to buy. Visible text should switch from "
                            "purchase timing to owned-game guidance. Always mention the user's playtime naturally when "
                            "ownership_context.playtime_label is available. Use these playtime modes: "
                            "UNPLAYED means 0 hours, say in Korean that the game is already in the library but has not "
                            "been played yet, then judge whether it is worth starting from backlog/taste fit. "
                            "LIGHTLY_PLAYED means over 0 and up to 20 hours, mention the playtime and explain that the "
                            "user sampled the early game but may not have fully committed; judge whether continuing is "
                            "worthwhile. MEANINGFULLY_PLAYED means over 20 and up to 100 hours, mention the playtime and "
                            "treat it as a game that likely fit at least somewhat; focus on revisit value rather than "
                            "base-game purchase value. PROVEN_FAVORITE means over 100 hours; do not analyze whether the "
                            "game fits the user as if unknown. Say it is already a proven taste signal, then focus on "
                            "revisit value, DLC/expansions/bundles, or using it as a reference for similar recommendations. "
                            "When the game is owned, price_reason and pattern_analysis may mention base-game price only "
                            "as low-priority context and should prefer DLC, expansions, bundles, or extra purchases if relevant. "
                            "For owned games, price_score should be 100 because the base game is already in the library; "
                            "final judgment should come from taste fit, Steam quality, and playtime context instead. "
                            "If pricing_context.is_free_to_play is true or analysis_mode is FREE_TO_PLAY, switch to a free-to-play "
                            "recommendation mode: use pattern_label FREE_TO_PLAY, do not call it a discount or historical-low deal, "
                            "do not say the user should wait for deeper discounts on the base game, and do not frame the main "
                            "question as purchase timing. In that case, price_score means low price barrier/free access rather "
                            "than deal quality and should be 100; decide recommendation_text from genre/tag fit, play-history fit, Steam quality "
                            "signals, multiplayer/team-play fit, time commitment, and possible monetization caveats such as DLC, "
                            "battle passes, skins, or in-game purchases. Use Korean phrases like '기본 게임은 상시 무료', "
                            "'무료라 가격 대기는 불필요', and '플레이해볼 만한지' when natural. "
                            "For user-facing text, never mention scoring mechanics or internal terms such as score, points, "
                            "weight, weighted, adjustment, boost, penalty, threshold, calculation, local score, model, or LLM. "
                            "Never mention numeric recommendation scores in visible text, including phrases like '78점', "
                            "'80점대', 'N/100', '점수를 준다면', or '적절한 점수'. "
                            "In taste_reason, write as if you interpreted the user's play history: mention concrete genre "
                            "and tag-based gameplay fit, play-history tendencies, and likely enjoyment, not why a numeric score changed. "
                            "When explaining taste fit, give slightly more influence to specific matched_tags/top_tags than broad genres, "
                            "because tags describe actual play feel more precisely. Use genres as the broad context and tags as the "
                            "main evidence when both are available, but do not let tags completely override genre mismatch, Steam "
                            "quality signals, or free-to-play monetization concerns. This does not mean listing more tags: in visible "
                            "Korean text, mention at most one or two especially meaningful tags, blend them into a natural sentence, "
                            "and avoid comma-separated tag dumps or long parenthetical tag lists. "
                            "Return only valid JSON with keys final_score, decision, price_score, taste_score, "
                            "quality_score, pattern_label, recommendation_text, price_reason, taste_reason, "
                            "pattern_analysis. Text values must be plain Korean strings."
                        ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_payload, ensure_ascii=False, default=_json_safe),
                },
            ],
            response_format={"type": "json_object"},
            timeout_seconds=PERSONALIZED_LLM_TIMEOUT_SECONDS,
        )
        data = json.loads(content)
        fallback = _fallback_personalized_text(game, analysis)
        adjusted = _apply_llm_adjustments(analysis, data)
        fallback = _fallback_personalized_text(game, adjusted)
        return adjusted, {
            "recommendation_text": _sanitize_user_facing_text(
                _llm_text(data.get("recommendation_text"), fallback["recommendation_text"]),
                fallback["recommendation_text"],
            ),
            "price_reason": _sanitize_user_facing_text(
                _llm_text(data.get("price_reason"), fallback["price_reason"]),
                fallback["price_reason"],
            ),
            "taste_reason": _sanitize_user_facing_text(
                _llm_text(data.get("taste_reason"), fallback["taste_reason"]),
                fallback["taste_reason"],
            ),
            "pattern_analysis": _sanitize_user_facing_text(
                _llm_text(data.get("pattern_analysis"), fallback["pattern_analysis"]),
                fallback["pattern_analysis"],
            ),
        }, "llm"
    except (GmsChatError, KeyError, ValueError, json.JSONDecodeError):
        return analysis, _fallback_personalized_text(game, analysis), "fallback"


def _generate_personalized_llm_text(game, analysis):
    _, text, source = _generate_personalized_llm_analysis(game, analysis)
    return text, source


def _apply_llm_adjustments(analysis, data):
    adjusted = dict(analysis)
    ownership_context = analysis.get("ownership_context") or {"is_owned": False}
    is_free_to_play = (
        analysis.get("pattern_label") == "FREE_TO_PLAY"
        or bool(analysis.get("price_features", {}).get("metrics", {}).get("is_free_to_play"))
    )
    local = {
        "score": int(analysis["score"]),
        "decision": analysis["decision"],
        "price_score": int(analysis["price_score"]),
        "taste_score": int(analysis["taste_score"]),
        "quality_score": int(analysis["quality_score"]),
        "pattern_label": analysis["pattern_label"],
    }

    pattern_label = str(data.get("pattern_label") or "").strip().upper()
    if pattern_label not in PURCHASE_PATTERN_LABELS:
        pattern_label = local["pattern_label"]
    if is_free_to_play:
        pattern_label = "FREE_TO_PLAY"
    elif pattern_label == "FREE_TO_PLAY":
        pattern_label = local["pattern_label"]

    if ownership_context.get("is_owned") or pattern_label == "FREE_TO_PLAY":
        price_score = 100
    else:
        price_score = _bounded_llm_int(data.get("price_score"), local["price_score"])
    taste_score = _bounded_llm_int(data.get("taste_score"), local["taste_score"])
    quality_score = _bounded_llm_int(data.get("quality_score"), local["quality_score"])
    score, scoring_context = _personalized_final_score(
        price_score=price_score,
        taste_score=taste_score,
        quality_score=quality_score,
        pattern_label=pattern_label,
        ownership_context=ownership_context,
    )
    decision = _decision(score)

    adjusted["score"] = score
    adjusted["decision"] = decision
    adjusted["price_score"] = price_score
    adjusted["taste_score"] = taste_score
    adjusted["quality_score"] = quality_score
    adjusted["pattern_label"] = pattern_label
    adjusted["metrics"] = {
        **analysis["metrics"],
        "llm_adjustment": {
            "local": local,
            "llm_requested_score": data.get("final_score"),
            "llm_requested_decision": data.get("decision"),
            "llm_requested_price_score": data.get("price_score"),
            "adjusted_score": score,
            "adjusted_decision": decision,
            "adjusted_price_score": price_score,
            "adjusted_taste_score": taste_score,
            "adjusted_quality_score": quality_score,
            "adjusted_pattern_label": pattern_label,
        },
        "scoring": scoring_context,
    }
    return adjusted


def _bounded_llm_int(value, fallback, lower=0, upper=100):
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = int(fallback)
    return max(lower, min(upper, number))


def _llm_text(value, fallback):
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, dict):
        for key in ("discount_pattern_text", "text", "summary", "reason", "content"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
        return json.dumps(value, ensure_ascii=False, default=_json_safe)
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _sanitize_user_facing_text(text, fallback):
    blocked_patterns = [
        r"\bLLM\b",
        r"\bmodel\b",
        r"\btaste\s*점수\b",
        r"\bscore\b",
        r"\d+\s*점",
        r"\d+\s*점대",
        r"\d+\s*/\s*100",
        r"점수",
        r"가중치",
        r"가중",
        r"상향",
        r"하향",
        r"보정",
        r"조정",
        r"계산",
        r"산식",
        r"임계",
        r"threshold",
        r"penalty",
        r"boost",
        r"local",
        r"다음\s*(할인|세일)",
        r"할인\s*예측",
        r"예상\s*구간",
        r"사이로\s*예상",
    ]
    if not isinstance(text, str):
        return fallback
    cleaned = text.strip()
    if not cleaned:
        return fallback
    if any(re.search(pattern, cleaned, re.IGNORECASE) for pattern in blocked_patterns):
        return fallback
    return cleaned


def price_fingerprint(game):
    steam_price = game.prices.select_related("store").filter(store__name__iexact="Steam").order_by("current_price").first()
    latest_history = (
        PriceHistory.objects.filter(game=game, store__name__iexact="Steam").order_by("-recorded_at").values_list("recorded_at", flat=True).first()
    )
    history_count = PriceHistory.objects.filter(game=game, store__name__iexact="Steam").count()
    latest_discount_event = (
        DiscountEvent.objects.filter(game=game, store__name__iexact="Steam").order_by("-started_at").values_list("started_at", flat=True).first()
    )
    discount_event_count = DiscountEvent.objects.filter(game=game, store__name__iexact="Steam").count()
    payload = {
        "steam_price": {
            "current_price": steam_price.current_price if steam_price else None,
            "original_price": steam_price.original_price if steam_price else None,
            "discount_rate": steam_price.discount_rate if steam_price else None,
            "historical_low_price": steam_price.historical_low_price if steam_price else None,
            "historical_low_date": steam_price.historical_low_date if steam_price else None,
            "updated_at": steam_price.updated_at if steam_price else None,
        },
        "history_count": history_count,
        "latest_history": latest_history,
        "discount_event_count": discount_event_count,
        "latest_discount_event": latest_discount_event,
    }
    raw = json.dumps(payload, sort_keys=True, default=_json_safe)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _recommendation_text(analysis):
    decision = analysis["decision"]
    if analysis.get("pattern_label") == "FREE_TO_PLAY" or analysis.get("metrics", {}).get("is_free_to_play"):
        if decision == "BUY":
            return "기본 게임은 상시 무료라 가격 대기는 불필요하고, 평가와 플레이 성향이 맞는다면 바로 시작해볼 만합니다."
        if decision == "CONSIDER":
            return "기본 게임은 무료로 접근할 수 있으니, 장르가 끌린다면 과금 구조와 플레이 방식을 확인하며 가볍게 시도해볼 만합니다."
        return "무료 게임이더라도 취향과 맞지 않으면 시간이 아까울 수 있어, 플레이 방식이 끌릴 때만 시도하는 편이 좋습니다."
    if decision == "BUY":
        return "현재 가격 조건이 역대 최저가 또는 강한 할인 구간에 가까워 지금 구매를 고려하기 좋습니다."
    if decision == "CONSIDER":
        return "현재도 나쁘지 않은 가격이지만, 더 깊은 할인을 기다릴 여지도 있습니다."
    return "현재 가격 조건만 보면 바로 구매하기보다 가격 메리트가 더 좋아질 때를 기다리는 편이 좋습니다."


def _serialize_ai_analysis(record, source):
    expires_at = record.generated_at + timedelta(days=AI_ANALYSIS_TTL_DAYS)
    return {
        "score": record.score,
        "decision": record.decision,
        "recommendation_text": record.recommendation_text,
        "pattern_label": record.pattern_label,
        "pattern_analysis": record.pattern_analysis,
        "metrics": record.metrics,
        "generated_at": record.generated_at,
        "expires_at": expires_at,
        "prompt_version": record.prompt_version,
        "source": source,
    }


def _serialize_personalized_analysis(record, source):
    expires_at = record.generated_at + timedelta(days=AI_ANALYSIS_TTL_DAYS)
    return {
        "score": record.score,
        "decision": record.decision,
        "recommendation_text": record.recommendation_text,
        "pattern_label": record.pattern_label,
        "pattern_analysis": record.pattern_analysis,
        "price_score": record.price_score,
        "taste_score": record.taste_score,
        "quality_score": record.quality_score,
        "price_reason": record.price_reason,
        "taste_reason": record.taste_reason,
        "metrics": record.metrics,
        "generated_at": record.generated_at,
        "expires_at": expires_at,
        "prompt_version": record.prompt_version,
        "source": source,
        "personalized": True,
    }


def _serialize_personalized_payload(analysis, text, source):
    generated_at = timezone.now()
    expires_at = generated_at + timedelta(days=AI_ANALYSIS_TTL_DAYS)
    return {
        "score": analysis["score"],
        "decision": analysis["decision"],
        "recommendation_text": text["recommendation_text"],
        "pattern_label": analysis["pattern_label"],
        "pattern_analysis": text["pattern_analysis"],
        "price_score": analysis["price_score"],
        "taste_score": analysis["taste_score"],
        "quality_score": analysis["quality_score"],
        "price_reason": text["price_reason"],
        "taste_reason": text["taste_reason"],
        "metrics": {**analysis["metrics"], "text_source": source},
        "generated_at": generated_at,
        "expires_at": expires_at,
        "prompt_version": PERSONALIZED_ANALYSIS_PROMPT_VERSION,
        "source": source,
        "personalized": True,
    }


def get_or_create_ai_analysis(game):
    fingerprint = price_fingerprint(game)
    minimum_generated_at = timezone.now() - timedelta(days=AI_ANALYSIS_TTL_DAYS)
    cached = getattr(game, "ai_analysis", None)
    if (
        cached
        and cached.prompt_version == AI_ANALYSIS_PROMPT_VERSION
        and cached.price_fingerprint == fingerprint
        and cached.generated_at >= minimum_generated_at
    ):
        return _serialize_ai_analysis(cached, "cache")

    analysis = analyze_purchase(game)
    pattern_analysis = _pattern_analysis_text(
        analysis.get("metrics", {}).get("discount_pattern_text") or analysis["explanation"],
        analysis.get("metrics", {}).get("next_discount_forecast") or {},
    )
    record, _ = GameAIAnalysis.objects.update_or_create(
        game=game,
        defaults={
            "score": analysis["score"],
            "decision": analysis["decision"],
            "recommendation_text": _recommendation_text(analysis),
            "pattern_label": analysis["pattern_label"],
            "pattern_analysis": pattern_analysis,
            "metrics": {key: _json_safe(value) for key, value in analysis.get("metrics", {}).items()},
            "price_fingerprint": fingerprint,
            "prompt_version": AI_ANALYSIS_PROMPT_VERSION,
        },
    )
    return _serialize_ai_analysis(record, "generated")


def get_or_create_personalized_ai_analysis(game, user):
    fingerprint = personalized_fingerprint(game, user)
    minimum_generated_at = timezone.now() - timedelta(days=AI_ANALYSIS_TTL_DAYS)
    cached = (
        UserGameAIAnalysis.objects.filter(
            game=game,
            user=user,
            prompt_version=PERSONALIZED_ANALYSIS_PROMPT_VERSION,
            input_fingerprint=fingerprint,
            generated_at__gte=minimum_generated_at,
        )
        .order_by("-generated_at")
        .first()
    )
    if cached:
        cached_text_source = (cached.metrics or {}).get("text_source")
        if cached_text_source != "fallback":
            return _serialize_personalized_analysis(cached, "cache")

    analysis = calculate_personalized_score(game, user)
    analysis, text, source = _generate_personalized_llm_analysis(game, analysis)
    if source == "fallback":
        return _serialize_personalized_payload(analysis, text, source)

    metrics = {**analysis["metrics"], "text_source": source}
    record, _ = UserGameAIAnalysis.objects.update_or_create(
        game=game,
        user=user,
        defaults={
            "score": analysis["score"],
            "price_score": analysis["price_score"],
            "taste_score": analysis["taste_score"],
            "quality_score": analysis["quality_score"],
            "decision": analysis["decision"],
            "recommendation_text": text["recommendation_text"],
            "price_reason": text["price_reason"],
            "taste_reason": text["taste_reason"],
            "pattern_label": analysis["pattern_label"],
            "pattern_analysis": text["pattern_analysis"],
            "metrics": metrics,
            "input_fingerprint": fingerprint,
            "prompt_version": PERSONALIZED_ANALYSIS_PROMPT_VERSION,
        },
    )
    return _serialize_personalized_analysis(record, source)


def personalized_games(user):
    owned = user.owned_games.select_related("game").prefetch_related("game__genres", "game__game_tags__tag")
    genre_weights = {}
    for item in owned:
        weight = max(1, item.playtime_minutes // 60)
        for genre in item.game.genres.all():
            genre_weights[genre.id] = genre_weights.get(genre.id, 0) + weight
    if not genre_weights:
        return (
            Game.objects.filter(related_product_entries__isnull=True)
            .prefetch_related("genres", "game_tags__tag", "prices__store")
            .order_by("-popularity_score")[:6]
        )
    top_genres = sorted(genre_weights, key=genre_weights.get, reverse=True)[:3]
    owned_ids = owned.values_list("game_id", flat=True)
    return (
        Game.objects.filter(genres__id__in=top_genres)
        .filter(related_product_entries__isnull=True)
        .exclude(id__in=owned_ids)
        .distinct()
        .prefetch_related("genres", "game_tags__tag", "prices__store")
        .order_by("-popularity_score")[:8]
    )


def personalized_home_games(user, limit=3):
    limit = max(1, min(int(limit or 3), 6))
    profile = build_user_taste_profile(user)
    top_genre_names = [item["name"] for item in profile.get("top_genres", [])[:5]]
    top_tag_names = [item["name"] for item in profile.get("top_tags", [])[:8]]
    if not top_genre_names and not top_tag_names:
        return []

    owned_ids = list(user.owned_games.values_list("game_id", flat=True))
    base_queryset = (
        Game.objects.filter(related_product_entries__isnull=True, prices__store__name__iexact="Steam")
        .exclude(id__in=owned_ids)
        .prefetch_related("genres", "game_tags__tag", "prices__store")
        .annotate(
            best_price=Min("prices__current_price", filter=Q(prices__store__name__iexact="Steam")),
            max_discount=Max("prices__discount_rate", filter=Q(prices__store__name__iexact="Steam")),
        )
    )

    taste_filter = Q()
    if top_genre_names:
        taste_filter |= Q(genres__name__in=top_genre_names)
    if top_tag_names:
        taste_filter |= Q(game_tags__tag__name__in=top_tag_names)

    candidates = list(
        base_queryset.filter(taste_filter)
        .distinct()
        .order_by("-steam_review_count", "-max_discount", "title")[:80]
    )
    if len(candidates) < limit:
        seen_ids = {game.id for game in candidates}
        fallback_candidates = (
            base_queryset.exclude(id__in=seen_ids)
            .distinct()
            .order_by("-max_discount", "-steam_review_count", "title")[:80]
        )
        candidates.extend(fallback_candidates)

    scored = []
    for game in candidates:
        taste_score, matched_genres, matched_tags = calculate_taste_score(game, profile)
        quality_score = calculate_quality_score(game)
        deal_score = _homepage_deal_score(game)
        final_score = int(
            (taste_score * HOME_RECOMMENDATION_WEIGHTS["taste"] / 100)
            + (quality_score * HOME_RECOMMENDATION_WEIGHTS["quality"] / 100)
            + (deal_score * HOME_RECOMMENDATION_WEIGHTS["deal"] / 100)
        )
        scored.append(
            {
                "game": game,
                "score": max(0, min(100, final_score)),
                "taste_score": taste_score,
                "quality_score": quality_score,
                "deal_score": deal_score,
                "matched_genres": matched_genres[:2],
                "matched_tags": matched_tags[:2],
                "reason": _homepage_recommendation_reason(game, matched_genres, matched_tags),
            }
        )

    return sorted(
        scored,
        key=lambda item: (
            item["score"],
            item["taste_score"],
            item["quality_score"],
            _homepage_discount_rate(item["game"]),
            item["game"].steam_review_count or 0,
        ),
        reverse=True,
    )[:limit]


def _homepage_deal_score(game):
    price = _homepage_steam_price(game)
    if not price:
        return 35
    if _is_free_to_play_price(price):
        return 65

    discount_rate = int(price.discount_rate or 0)
    current_price = _decimal_amount(price.current_price)
    historical_low = _decimal_amount(price.historical_low_price or 0)
    score = 35 + int(min(discount_rate, 70) * Decimal("0.7"))

    if historical_low > 0:
        if current_price <= historical_low:
            score += 14
        else:
            current_vs_low = current_price / historical_low
            if current_vs_low <= Decimal("1.1"):
                score += 8
            elif current_vs_low >= Decimal("1.4") and discount_rate < 30:
                score -= 8
    if discount_rate <= 0:
        score = min(score, 45)
    return max(0, min(100, int(score)))


def _homepage_recommendation_reason(game, matched_genres, matched_tags):
    discount_rate = _homepage_discount_rate(game)
    if matched_tags:
        base = f"{matched_tags[0]['name']} 취향과 잘 맞아요."
    elif matched_genres:
        base = f"{matched_genres[0]['name']} 선호와 잘 맞아요."
    else:
        base = "평가와 가격 조건이 안정적이에요."

    if discount_rate >= 50:
        return f"{base} 할인도 꽤 좋아요."
    if discount_rate > 0:
        return f"{base} 현재 할인 중이에요."
    return base


def _homepage_discount_rate(game):
    price = _homepage_steam_price(game)
    return int(price.discount_rate or 0) if price else 0


def _homepage_steam_price(game):
    prefetched = getattr(game, "_prefetched_objects_cache", {})
    if "prices" in prefetched:
        prices = [price for price in prefetched["prices"] if price.store.name.lower() == "steam"]
    else:
        prices = list(game.prices.filter(store__name__iexact="Steam").select_related("store"))
    if not prices:
        return None
    return sorted(prices, key=lambda price: price.current_price)[0]


def generate_chat_reply(message, user=None, history=None):
    message = (message or "").strip()
    if not message:
        return {"reply": "궁금한 게임이나 할인 조건을 입력해 주세요.", "source": "fallback"}

    context = _chat_context(message, user, history)
    fallback = _local_chat_reply(message, context)
    is_user_taste_discounted = bool(context.get("intent", {}).get("user_taste_discounted"))
    if is_user_taste_discounted and (
        not context.get("user", {}).get("has_owned_games") or not context.get("matched_games")
    ):
        return {"reply": fallback, "source": "fallback"}

    api_key = os.getenv("GMS_KEY", "").strip()
    if not api_key:
        return {"reply": fallback, "source": "fallback"}

    base_url = os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL).strip().rstrip("/")
    model = os.getenv("CHAT_LLM_MODEL", DEFAULT_CHAT_LLM_MODEL).strip()
    messages = [
        {
            "role": "system",
            "content": (
                "You are Critical AI, a concise Korean game deal assistant for Critical Deal. "
                "Understand the user's intent, constraints, and recent conversation, then answer in Korean. "
                "Use only local_context and local_answer for factual claims. "
                "Never recommend a game that is not present in matched_games or similar_discounted_games. "
                "For recommendation questions, choose two to four candidates that best match the parsed constraints, "
                "mention the reason for each pick, and avoid repeating a default favorite. "
                "For discount prediction questions, give the estimated window from discount_forecast, explain the basis, "
                "and clearly say it is an estimate rather than a promise. "
                "If a game is marked is_free_to_play, explain that the base game is permanently free-to-play instead of "
                "framing it as a discount or purchase-timing question. "
                "If recommendation_mode is USER_TASTE_DISCOUNTED, recommend only matched_games as discounted games selected "
                "from the user's owned games and play-history taste profile. Use recommendation details inside each matched "
                "game to explain why it fits, but do not mention numeric scores. Do not copy local_answer mechanically; write "
                "a natural recommendation that compares fit, discount appeal, and Steam quality briefly. Do not use "
                "matched_games[0] as a game the user played, and never claim the user played a title unless it appears in "
                "local_context.user.top_owned_titles. "
                "For similar discounted game questions, recommend games from similar_discounted_games and explain why "
                "they are similar to the referenced game. "
                "If local_context says exact matches were not found, say that before offering nearby alternatives. "
                "Do not invent prices, discounts, dates, stores, or games. If data is missing, say what is missing. "
                "Return only valid JSON with key reply. Keep the reply under 6 short sentences."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "local_context": context,
                    "local_answer": fallback,
                    "recent_messages": [] if is_user_taste_discounted else _chat_history(history),
                    "history_policy": (
                        "Ignore previous assistant messages as recommendation evidence for USER_TASTE_DISCOUNTED."
                        if is_user_taste_discounted
                        else "Use recent messages only for conversational continuity."
                    ),
                    "question": message,
                },
                ensure_ascii=False,
                default=_json_safe,
            ),
        },
    ]
    try:
        reply = _post_gms_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            timeout_seconds=CHAT_LLM_TIMEOUT_SECONDS,
        )
        data = json.loads(reply)
        polished = (data.get("reply") or "").strip()
        if _is_bad_chat_reply(polished, context) or (
            is_user_taste_discounted and _chat_reply_uses_disallowed_title(polished, context)
        ):
            return {"reply": fallback, "source": "fallback"}
        return {"reply": polished, "source": "llm"}
    except (GmsChatError, KeyError, ValueError, json.JSONDecodeError):
        return {"reply": fallback, "source": "fallback"}


def _chat_history(history):
    cleaned = []
    for item in (history or [])[-CHAT_HISTORY_LIMIT:]:
        role = item.get("role")
        content = (item.get("text") or item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content[:500]})
    return cleaned


def _chat_context(message, user, history=None):
    from games.services import game_queryset

    context_text = _chat_context_text(message, history)
    intent = _chat_intent(message, context_text)
    constraints = _chat_constraints(message)
    exact_matches_found = False

    if intent["user_taste_discounted"]:
        profile = {"terms": [], "title_hints": [], "genres": [], "tags": [], "avoid_genres": []}
        terms = []
        games = _chat_personalized_discounted_games(user)
        exact_matches_found = bool(games)
    else:
        profile = _chat_query_profile(message, context_text)
        terms = profile["terms"]
        query = _chat_game_query(profile)
        games_queryset = game_queryset(include_related_products=False)
        if query is not None:
            games_queryset = games_queryset.filter(query).distinct()
            games_queryset = _apply_chat_constraints(games_queryset, constraints, intent)
            candidates = list(
                games_queryset.order_by("-steam_review_count", "-popularity_score", "best_price")[
                    :CHAT_CONTEXT_CANDIDATE_LIMIT
                ]
            )
            exact_matches_found = bool(candidates)
        else:
            games_queryset = _apply_chat_constraints(games_queryset, constraints, intent, default_discounted=True)
            candidates = list(
                games_queryset.order_by("-steam_review_count", "-popularity_score", "best_price")[
                    :CHAT_CONTEXT_CANDIDATE_LIMIT
                ]
            )

        reference_games = []
        if query is not None and (intent.get("similar_discounted") or intent.get("discount_prediction")):
            reference_candidates = list(
                game_queryset(include_related_products=False)
                .filter(query)
                .distinct()
                .prefetch_related("genres", "game_tags__tag", "prices__store")
                .order_by("-steam_review_count", "-popularity_score", "best_price")[:CHAT_CONTEXT_CANDIDATE_LIMIT]
            )
            reference_games = _rank_chat_games(
                message,
                reference_candidates,
                profile,
                {"max_price": None, "min_discount": None, "free_only": False, "wants_discounted": False},
                {**intent, "recommendation": False},
            )

        games = _rank_chat_games(message, candidates, profile, constraints, intent)[:CHAT_RECOMMENDATION_LIMIT]
        if reference_games:
            primary_reference = reference_games[0]
            games = [primary_reference] + [game for game in games if game.id != primary_reference.id]
            games = games[:CHAT_RECOMMENDATION_LIMIT]
            exact_matches_found = True
        if not games:
            games = _default_chat_games(user, constraints=constraints, intent=intent)
            exact_matches_found = False

    owned_titles = []
    top_genres = []
    top_tags = []
    owned_count = 0
    if user and user.is_authenticated:
        owned_queryset = user.owned_games.select_related("game")
        owned_count = owned_queryset.count()
        owned_titles = list(owned_queryset.order_by("-playtime_minutes").values_list("game__title", flat=True)[:8])
        profile_for_user = build_user_taste_profile(user)
        top_genres = profile_for_user.get("top_genres", [])[:5]
        top_tags = profile_for_user.get("top_tags", [])[:6]

    primary_game = games[0] if games else None
    return {
        "search_terms": terms,
        "understanding": {
            "used_history_context": context_text != message,
            "exact_matches_found": exact_matches_found,
            "constraints": constraints,
            "genres": profile["genres"],
            "tags": profile["tags"],
            "title_hints": profile["title_hints"],
        },
        "intent": intent,
        "recommendation_mode": "USER_TASTE_DISCOUNTED" if intent["user_taste_discounted"] else "DEFAULT",
        "recommendation_basis": (
            {
                "candidate_source": "discounted Steam games excluding owned games",
                "ranking_policy": "taste first, then Steam quality, then discount appeal",
                "weights": HOME_RECOMMENDATION_WEIGHTS,
            }
            if intent["user_taste_discounted"]
            else {}
        ),
        "matched_games": [_chat_game_item(game) for game in games],
        "discount_forecast": _chat_discount_forecast(primary_game) if primary_game and intent["discount_prediction"] else None,
        "similar_discounted_games": (
            [_chat_game_item(game) for game in _chat_similar_discounted_games(primary_game, message)]
            if primary_game and intent["similar_discounted"] and not intent["user_taste_discounted"]
            else []
        ),
        "user": {
            "authenticated": bool(user and user.is_authenticated),
            "owned_count": owned_count,
            "has_owned_games": owned_count > 0,
            "top_owned_titles": owned_titles,
            "top_genres": top_genres,
            "top_tags": top_tags,
        },
    }


def _chat_context_text(message, history):
    recent_user_messages = [
        (item.get("text") or item.get("content") or "").strip()
        for item in (history or [])[-CHAT_HISTORY_LIMIT:]
        if item.get("role") == "user" and (item.get("text") or item.get("content"))
    ]
    if not recent_user_messages:
        return message
    lowered = (message or "").lower()
    needs_history = any(marker in lowered for marker in ["그거", "그 게임", "그럼", "걔", "얘", "비슷한거", "비슷한 것", "그 중"])
    if needs_history:
        return " ".join(recent_user_messages[-2:] + [message])
    return message


def _chat_query_profile(message, context_text=None, allow_history=True):
    text = context_text if allow_history and context_text else message
    excluded_aliases = _chat_excluded_alias_keys(text)
    alias_match = _chat_alias_match(text) or _chat_alias_match(message)
    alias = alias_match[1] if alias_match and alias_match[0] not in excluded_aliases else None
    terms = []
    title_hints = []
    genres = []
    tags = []
    avoid_genres = []

    if alias:
        terms.extend(alias.get("terms", []))
        title_hints.extend(alias.get("title_hints", []))
        genres.extend(alias.get("genre_hints", []))
        avoid_genres.extend(alias.get("avoid_genres", []))

    terms.extend(_chat_search_terms(text, ignore_alias=bool(excluded_aliases)))
    compact = (text or "").lower().replace(" ", "")
    lowered = (text or "").lower()
    for key, names in CHAT_GENRE_ALIASES.items():
        if key in lowered or key.replace(" ", "") in compact:
            genres.extend(names)
    for key, names in CHAT_TAG_ALIASES.items():
        if key in lowered or key.replace(" ", "") in compact:
            tags.extend(names)

    return {
        "terms": _unique_preserve_order(terms),
        "title_hints": _unique_preserve_order(title_hints),
        "genres": _unique_preserve_order(genres),
        "tags": _unique_preserve_order(tags),
        "avoid_genres": _unique_preserve_order(avoid_genres),
    }


def _chat_game_query(profile):
    query = None
    for term in profile.get("terms", [])[:8]:
        part = Q(title__icontains=term) | Q(genres__name__icontains=term) | Q(tags__name__icontains=term)
        query = part if query is None else query | part
    for hint in profile.get("title_hints", [])[:6]:
        part = Q(title__icontains=hint)
        query = part if query is None else query | part
    for genre in profile.get("genres", [])[:8]:
        part = Q(genres__name__iexact=genre) | Q(genres__name__icontains=genre)
        query = part if query is None else query | part
    for tag in profile.get("tags", [])[:16]:
        part = Q(tags__name__iexact=tag) | Q(tags__name__icontains=tag)
        query = part if query is None else query | part
    return query


def _chat_constraints(message):
    lowered = (message or "").lower()
    max_price = _chat_price_limit(lowered)
    min_discount = _chat_discount_limit(lowered)
    free_only = any(keyword in lowered for keyword in ["무료", "공짜", "0원"])
    excluded_title_hints = _chat_excluded_title_hints(message)
    wants_discounted = any(
        keyword in lowered
        for keyword in ["할인중", "할인 중", "세일중", "세일 중", "특가", "할인하는", "할인 게임", "할인작", "세일 게임"]
    )
    return {
        "max_price": max_price,
        "min_discount": min_discount,
        "free_only": free_only,
        "wants_discounted": wants_discounted or min_discount is not None,
        "excluded_title_hints": excluded_title_hints,
    }


def _chat_price_limit(lowered):
    compact = lowered.replace(" ", "")
    if any(keyword in compact for keyword in ["만원이하", "1만원이하", "만 원이하", "10000원이하"]):
        return 10000
    match = re.search(r"(\d+(?:\.\d+)?)\s*만\s*원?\s*(?:이하|안쪽|미만|까지)?", lowered)
    if match:
        return int(float(match.group(1)) * 10000)
    match = re.search(r"(\d{1,3}(?:,\d{3})+|\d{4,6})\s*원?\s*(?:이하|안쪽|미만|까지)", lowered)
    if match:
        return int(match.group(1).replace(",", ""))
    match = re.search(r"under\s*(\d+)", lowered)
    if match:
        return int(match.group(1))
    return None


def _chat_discount_limit(lowered):
    match = re.search(r"(\d{1,2})\s*%\s*(?:이상|넘|할인)", lowered)
    if match:
        return int(match.group(1))
    return None


def _apply_chat_constraints(games, constraints, intent, default_discounted=False):
    price_filter = Q(prices__store__name__iexact="Steam")
    if constraints.get("free_only"):
        price_filter &= Q(prices__current_price=0)
    else:
        price_filter &= Q(prices__current_price__gte=0)
        if constraints.get("max_price") is not None:
            price_filter &= Q(prices__current_price__lte=constraints["max_price"])
    if constraints.get("min_discount") is not None:
        price_filter &= Q(prices__discount_rate__gte=constraints["min_discount"])
    elif constraints.get("wants_discounted") or (default_discounted and intent.get("recommendation")):
        price_filter &= Q(prices__discount_rate__gt=0)
    games = games.filter(price_filter)
    for hint in constraints.get("excluded_title_hints") or []:
        games = games.exclude(title__icontains=hint)
    return games.distinct()


def _rank_chat_games(message, games, profile, constraints, intent):
    if not games:
        return []
    quality_pool = [
        game
        for game in games
        if int(game.steam_review_count or 0) >= CHAT_MIN_QUALITY_REVIEW_COUNT or int(game.steam_review_score or 0) >= 75
    ]
    if len(quality_pool) >= min(CHAT_RECOMMENDATION_LIMIT, len(games)):
        games = quality_pool
    return sorted(games, key=lambda game: _chat_candidate_score(game, profile, constraints, intent), reverse=True)


def _chat_candidate_score(game, profile, constraints, intent):
    price = _chat_steam_price(game)
    title = game.title.lower()
    genres = {genre.name for genre in game.genres.all()}
    tags = {tag["name"] for tag in _game_tag_items(game, limit=12)}
    lower_tags = {tag.lower() for tag in tags}
    lower_genres = {genre.lower() for genre in genres}

    score = 0.0
    for hint in profile.get("title_hints", []):
        if hint.lower() in title:
            score += 120
    for term in profile.get("terms", []):
        lowered = term.lower()
        if lowered in title:
            score += 85
        if lowered in lower_tags or lowered in lower_genres:
            score += 45
    for genre in profile.get("genres", []):
        if genre.lower() in lower_genres:
            score += 55
    for tag in profile.get("tags", []):
        tag_lower = tag.lower()
        if tag_lower in lower_tags:
            score += 45
        elif any(tag_lower in item for item in lower_tags):
            score += 25

    review_count = int(game.steam_review_count or 0)
    review_score = int(game.steam_review_score or 0)
    if review_count:
        score += min(45, review_count ** 0.35)
    if review_score:
        score += max(0, review_score - 60) * 0.9
    if review_count < 20 and not profile.get("title_hints"):
        score -= 45

    if price:
        discount_rate = int(price.discount_rate or 0)
        current_price = Decimal(price.current_price or 0)
        score += discount_rate * (0.75 if constraints.get("wants_discounted") or intent.get("recommendation") else 0.3)
        if constraints.get("max_price"):
            budget = Decimal(str(constraints["max_price"]))
            if current_price <= budget:
                score += min(20, float((budget - current_price) / max(budget, Decimal("1")) * 20))
        elif current_price > 0:
            score += max(0, 12 - min(12, float(current_price) / 10000))
    score += min(20, int(game.popularity_score or 0) / 100)
    return score


def _chat_intent(message, context_text=None):
    lowered = (message or "").lower()
    context_lowered = (context_text or message or "").lower()
    prediction_keywords = ["다음 할인", "할인 기간", "할인 예측", "언제 할인", "세일 언제", "다음 세일", "할인 언제"]
    similar_keywords = ["같은", "비슷", "유사", "대체", "스타일", "느낌", "류", "닮은", "like"]
    history_reference_keywords = ["그거", "그 게임", "그럼", "걔", "얘", "비슷한거", "비슷한 것", "그 중"]
    discount_keywords = ["할인", "세일", "특가"]
    recommendation_keywords = ["추천", "뭐 살", "뭘 살", "살만", "골라", "pick", "recommend", "찾아줘"]
    user_taste_keywords = [
        "내가 한",
        "내가 했",
        "내가 할",
        "내 게임",
        "내 취향",
        "내 스타일",
        "나한테",
        "취향 기반",
        "플레이한",
        "플레이 기록",
        "보유 게임",
        "라이브러리",
        "한 게임 기반",
    ]
    user_taste_discounted = (
        any(keyword in lowered for keyword in user_taste_keywords)
        and any(keyword in lowered for keyword in recommendation_keywords)
        and any(keyword in lowered for keyword in discount_keywords)
    )
    current_has_similar = any(keyword in lowered for keyword in similar_keywords)
    history_has_similar_reference = any(keyword in lowered for keyword in history_reference_keywords) and any(
        keyword in context_lowered for keyword in similar_keywords
    )
    return {
        "discount_prediction": any(keyword in lowered for keyword in prediction_keywords),
        "similar_discounted": (
            not user_taste_discounted
            and (current_has_similar or history_has_similar_reference)
            and any(keyword in lowered for keyword in discount_keywords + recommendation_keywords)
        ),
        "user_taste_discounted": user_taste_discounted,
        "recommendation": any(keyword in lowered for keyword in recommendation_keywords),
    }


def _chat_alias(message):
    match = _chat_alias_match(message)
    return match[1] if match else None


def _chat_alias_match(message):
    lowered = (message or "").lower().replace(" ", "")
    for alias, config in CHAT_GAME_ALIASES.items():
        if alias.replace(" ", "") in lowered:
            return alias, config
    return None


def _chat_excluded_alias_keys(message):
    lowered = (message or "").lower()
    compact = lowered.replace(" ", "")
    negative_keywords = ["말고", "빼고", "제외", "빼면", "말고는", "not", "except"]
    if not any(keyword in lowered for keyword in negative_keywords):
        return set()
    excluded = set()
    for alias in CHAT_GAME_ALIASES:
        compact_alias = alias.replace(" ", "").lower()
        if compact_alias and compact_alias in compact:
            excluded.add(alias)
    return excluded


def _chat_excluded_title_hints(message):
    hints = []
    for alias in _chat_excluded_alias_keys(message):
        config = CHAT_GAME_ALIASES.get(alias, {})
        hints.append(alias)
        hints.extend(config.get("title_hints", []))
        hints.extend(config.get("terms", []))
    return _unique_preserve_order(hints)


def _chat_search_terms(message, ignore_alias=False):
    stopwords = {
        "게임",
        "게임을",
        "게임이",
        "게임은",
        "게임도",
        "게임중",
        "게임들",
        "추천",
        "추천해줘",
        "할인",
        "할인중",
        "할인중인",
        "세일중",
        "세일중인",
        "가격",
        "정보",
        "어때",
        "살까",
        "사지",
        "지금",
        "구매",
        "분석",
        "알려줘",
        "뭐",
        "좀",
        "해주세요",
        "해줘",
        "같은",
        "비슷한",
        "하고",
        "있는",
        "중에",
        "중인",
        "기간",
        "예측",
        "다음",
        "세일",
        "언제",
        "언제야",
        "이하",
        "미만",
        "까지",
        "만원",
        "만",
        "원",
        "할인하는",
        "좋은",
        "재밌는",
        "괜찮은",
        "없어",
        "있어",
        "찾아줘",
        "그거",
        "그",
        "말고",
        "빼고",
        "제외",
        "내가",
        "내",
        "한",
        "할",
        "만한",
        "기반",
        "기반으로",
        "취향",
        "보유",
        "플레이",
        "라이브러리",
        "현재",
    }
    alias = None if ignore_alias else _chat_alias(message)
    if alias:
        return alias.get("terms", [])
    terms = []
    for term in re_split_query(message):
        normalized = term.strip().lower()
        if len(normalized) < 2 or normalized in stopwords:
            continue
        terms.append(normalized)
    return terms


def _default_chat_games(user, constraints=None, intent=None):
    constraints = constraints or {}
    intent = intent or {"recommendation": True}
    if user and user.is_authenticated and user.owned_games.exists() and not constraints.get("free_only"):
        candidates = list(personalized_games(user)[:CHAT_RECOMMENDATION_LIMIT])
        if candidates:
            return candidates
    games = (
        Game.objects.prefetch_related("genres", "game_tags__tag", "prices__store")
        .filter(related_product_entries__isnull=True)
    )
    games = _apply_chat_constraints(games, constraints, intent, default_discounted=True)
    candidates = list(
        games.distinct().order_by("-steam_review_count", "-popularity_score", "prices__current_price")[
            :CHAT_CONTEXT_CANDIDATE_LIMIT
        ]
    )
    return _rank_chat_games("", candidates, {"terms": [], "title_hints": [], "genres": [], "tags": []}, constraints, intent)[
        :CHAT_RECOMMENDATION_LIMIT
    ]


def _chat_personalized_discounted_games(user, limit=CHAT_RECOMMENDATION_LIMIT):
    if not user or not user.is_authenticated or not user.owned_games.exists():
        return []

    profile = build_user_taste_profile(user)
    top_genre_names = [item["name"] for item in profile.get("top_genres", [])[:5]]
    top_tag_names = [item["name"] for item in profile.get("top_tags", [])[:8]]
    if not top_genre_names and not top_tag_names:
        return []

    taste_filter = Q()
    if top_genre_names:
        taste_filter |= Q(genres__name__in=top_genre_names)
    if top_tag_names:
        taste_filter |= Q(tags__name__in=top_tag_names)

    owned_ids = list(user.owned_games.values_list("game_id", flat=True))
    candidates = list(
        Game.objects.filter(
            taste_filter,
            related_product_entries__isnull=True,
            prices__store__name__iexact="Steam",
            prices__current_price__gt=0,
            prices__discount_rate__gt=0,
        )
        .exclude(id__in=owned_ids)
        .distinct()
        .prefetch_related("genres", "game_tags__tag", "prices__store")[:120]
    )

    scored = []
    for game in candidates:
        taste_score, matched_genres, matched_tags = calculate_taste_score(game, profile)
        quality_score = calculate_quality_score(game)
        deal_score = _homepage_deal_score(game)
        final_score = int(
            (taste_score * HOME_RECOMMENDATION_WEIGHTS["taste"] / 100)
            + (quality_score * HOME_RECOMMENDATION_WEIGHTS["quality"] / 100)
            + (deal_score * HOME_RECOMMENDATION_WEIGHTS["deal"] / 100)
        )
        price = _chat_steam_price(game)
        game._chat_recommendation_context = {
            "taste_score": taste_score,
            "quality_score": quality_score,
            "deal_score": deal_score,
            "matched_genres": matched_genres[:2],
            "matched_tags": matched_tags[:3],
            "reason": _homepage_recommendation_reason(game, matched_genres, matched_tags),
        }
        scored.append(
            (
                final_score,
                taste_score,
                quality_score,
                int(price.discount_rate or 0) if price else 0,
                int(game.steam_review_count or 0),
                game,
            )
        )

    scored = sorted(
        scored,
        key=lambda item: (item[0], item[1], item[2], item[3], item[4], item[5].title),
        reverse=True,
    )
    return [item[-1] for item in scored[:limit]]


def _chat_discount_forecast(game):
    if not game:
        return None

    steam_price = _chat_steam_price(game)
    if _is_free_to_play_price(steam_price):
        return {
            "game": game.title,
            "has_enough_history": False,
            "is_free_to_play": True,
            "current_price": steam_price.current_price,
            "current_discount_rate": steam_price.discount_rate,
            "message": "기본 게임은 상시 무료라 다음 할인 예측은 적용하지 않습니다.",
        }

    history = list(
        PriceHistory.objects.filter(game=game, store__name__iexact="Steam")
        .order_by("recorded_at")
        .values("recorded_at", "price", "discount_rate")
    )
    discounted = [item for item in history if int(item["discount_rate"] or 0) > 0]
    today = timezone.localdate()

    if len(discounted) < 2:
        return {
            "game": game.title,
            "has_enough_history": False,
            "current_price": steam_price.current_price if steam_price else None,
            "current_discount_rate": steam_price.discount_rate if steam_price else 0,
            "history_count": len(history),
            "discount_count": len(discounted),
            "message": "할인 이력이 충분하지 않아 다음 할인 시점을 좁혀 예측하기 어렵습니다.",
        }

    discount_dates = [item["recorded_at"] for item in discounted]
    intervals = [(discount_dates[i] - discount_dates[i - 1]).days for i in range(1, len(discount_dates))]
    avg_interval = max(1, int(sum(intervals) / len(intervals)))
    last_discount_date = discount_dates[-1]
    estimated_next_date = last_discount_date + timedelta(days=avg_interval)
    window_start = estimated_next_date - timedelta(days=max(7, avg_interval // 5))
    window_end = estimated_next_date + timedelta(days=max(7, avg_interval // 5))
    days_since_last = (today - last_discount_date).days
    confidence = "high" if len(discounted) >= 6 and avg_interval <= 120 else "medium" if len(discounted) >= 3 else "low"

    return {
        "game": game.title,
        "has_enough_history": True,
        "current_price": steam_price.current_price if steam_price else None,
        "current_discount_rate": steam_price.discount_rate if steam_price else 0,
        "historical_low_price": steam_price.historical_low_price if steam_price else None,
        "last_discount_date": last_discount_date,
        "days_since_last_discount": days_since_last,
        "average_discount_interval_days": avg_interval,
        "discount_count": len(discounted),
        "estimated_next_discount_window": {
            "start": window_start,
            "center": estimated_next_date,
            "end": window_end,
        },
        "confidence": confidence,
    }


def _chat_similar_discounted_games(game, message="", limit=5):
    if not game:
        return []
    genre_names = _chat_genre_names_for_similarity(game, message)
    tag_names = [item["name"] for item in _game_tag_items(game, limit=8)]
    avoid_genres = set(_chat_avoid_genres_for_similarity(message))
    if not genre_names and not tag_names:
        return []

    candidate_filter = Q(prices__store__name__iexact="Steam", prices__discount_rate__gt=0, steam_review_count__gte=100)
    if genre_names and tag_names:
        candidate_filter &= Q(genres__name__in=genre_names) | Q(tags__name__in=tag_names)
    elif genre_names:
        candidate_filter &= Q(genres__name__in=genre_names)
    else:
        candidate_filter &= Q(tags__name__in=tag_names)

    candidates = list(
        Game.objects.filter(candidate_filter)
        .filter(related_product_entries__isnull=True)
        .exclude(id=game.id)
        .distinct()
        .prefetch_related("genres", "game_tags__tag", "prices__store")[:80]
    )

    genre_set = set(genre_names)
    tag_set = set(tag_names)

    def score(candidate):
        candidate_genres = {genre.name for genre in candidate.genres.all()}
        candidate_tags = {item["name"] for item in _game_tag_items(candidate, limit=8)}
        overlap = len(genre_set & candidate_genres)
        tag_overlap = len(tag_set & candidate_tags)
        avoided_overlap = len(avoid_genres & candidate_genres)
        price = _chat_steam_price(candidate)
        discount_rate = int(price.discount_rate or 0) if price else 0
        return (
            tag_overlap,
            overlap,
            -avoided_overlap,
            int(candidate.steam_review_score or 0),
            min(int(candidate.steam_review_count or 0), 50000),
            discount_rate,
        )

    return sorted(candidates, key=score, reverse=True)[:limit]


def _chat_genre_names_for_similarity(game, message):
    alias = _chat_alias(message)
    if alias and alias.get("genre_hints"):
        return alias["genre_hints"]

    genre_names = list(game.genres.values_list("name", flat=True))
    if genre_names:
        return genre_names
    title = game.title.lower()
    for config in CHAT_GAME_ALIASES.values():
        if all(hint in title for hint in config.get("title_hints", [])):
            return config.get("genre_hints", [])
    return []


def _chat_avoid_genres_for_similarity(message):
    alias = _chat_alias(message)
    if alias:
        return alias.get("avoid_genres", [])
    return []


def _chat_steam_price(game):
    prefetched = getattr(game, "_prefetched_objects_cache", {})
    if "prices" in prefetched:
        prices = [price for price in prefetched["prices"] if price.store.name.lower() == "steam"]
        return sorted(prices, key=lambda item: item.current_price)[0] if prices else None
    return game.prices.select_related("store").filter(store__name__iexact="Steam").order_by("current_price").first()


def _chat_game_item(game):
    price = _chat_steam_price(game)
    item = {
        "id": game.id,
        "title": game.title,
        "genres": [genre.name for genre in game.genres.all()],
        "tags": [tag["name"] for tag in _game_tag_items(game, limit=8)],
        "current_price": price.current_price if price else None,
        "original_price": price.original_price if price else None,
        "discount_rate": price.discount_rate if price else 0,
        "is_free_to_play": _is_free_to_play_price(price),
        "steam_review_score": game.steam_review_score,
        "steam_review_count": game.steam_review_count,
    }
    recommendation = getattr(game, "_chat_recommendation_context", None)
    if recommendation:
        item["recommendation"] = recommendation
    return item


def _local_chat_reply(message, context):
    games = context.get("matched_games", [])
    if context.get("intent", {}).get("user_taste_discounted"):
        user_context = context.get("user", {})
        if not user_context.get("authenticated") or not user_context.get("has_owned_games"):
            return "사용자 취향 기반 추천을 하려면 Steam 계정 연동이나 보유 게임 데이터가 필요합니다. 연동 후에는 플레이 기록의 장르와 태그를 기준으로 현재 할인 중인 게임만 추려드릴 수 있어요."
        if not games:
            return "보유 게임과 플레이 기록을 기준으로 현재 할인 중인 추천 후보를 찾지 못했습니다. Steam 라이브러리 동기화가 오래됐다면 다시 동기화한 뒤 확인해 주세요."
        picks = [_chat_pick_sentence(game, index + 1) for index, game in enumerate(games[:3])]
        return (
            "Steam 보유 게임과 플레이 기록에서 나온 취향을 기준으로, 현재 할인 중인 게임 중에는 "
            + " ".join(picks)
            + " 취향 적합도를 먼저 보고, 할인율과 Steam 평가를 보조로 반영했습니다."
        )

    if not games:
        return "로컬 데이터에서 관련 게임을 찾지 못했습니다. 게임명을 더 정확히 입력하거나 원하는 장르, 예산, 할인율을 함께 알려 주세요."

    if context.get("intent", {}).get("discount_prediction"):
        forecast = context.get("discount_forecast") or {}
        if forecast.get("is_free_to_play"):
            return f"{forecast['game']}은 기본 게임이 상시 무료라 다음 할인 시점을 기다리는 방식의 분석은 맞지 않습니다. DLC, 배틀패스, 스킨 같은 선택 과금만 별도로 확인하면 됩니다."
        if not forecast.get("has_enough_history"):
            return f"{games[0]['title']}은 저장된 할인 이력이 부족해 다음 할인 기간을 좁혀 예측하기 어렵습니다. 현재 가격과 할인율을 기준으로만 확인해 주세요."
        window = forecast["estimated_next_discount_window"]
        return (
            f"{forecast['game']}의 다음 할인은 이력 기준으로 {window['start']}부터 {window['end']} 사이를 예상할 수 있습니다. "
            f"마지막 할인은 {forecast['last_discount_date']}였고, 평균 할인 간격은 약 {forecast['average_discount_interval_days']}일입니다. "
            f"예측 신뢰도는 {forecast['confidence']}이며 실제 Steam 세일 일정에 따라 달라질 수 있습니다."
        )

    if context.get("intent", {}).get("similar_discounted"):
        similar_games = context.get("similar_discounted_games") or []
        if similar_games:
            picks = [_chat_pick_sentence(game, index + 1) for index, game in enumerate(similar_games[:3])]
            if _chat_alias(message):
                return f"{games[0]['title']}와 정확히 같은 결의 할인작은 적어서, 현재 할인 중인 게임 중 장르 접점이 있는 후보로는 " + " ".join(picks)
            return f"{games[0]['title']}와 장르가 겹치면서 현재 할인 중인 게임은 " + " ".join(picks)
        return f"{games[0]['title']}와 장르가 겹치는 현재 할인 게임을 로컬 데이터에서 찾지 못했습니다."

    if _is_recommendation_question(message) or not context.get("search_terms"):
        picks = [_chat_pick_sentence(game, index + 1) for index, game in enumerate(games[:3])]
        return "로컬 할인 데이터 기준으로는 " + " ".join(picks) + " 더 정확히 고르려면 선호 장르나 예산을 같이 알려 주세요."

    game = games[0]
    if game["current_price"] is None:
        return f"{game['title']} 정보는 찾았지만 현재 Steam 가격 데이터가 부족해요. 가격 동기화 후 다시 물어봐 주세요."
    if game.get("is_free_to_play"):
        review = ""
        if game.get("steam_review_score") and game.get("steam_review_count"):
            review = f" Steam 평가는 {game['steam_review_score']}점, 리뷰 {game['steam_review_count']:,}개 기준입니다."
        return f"{game['title']}은 기본 게임이 상시 무료인 부분유료화 게임으로 보입니다.{review} 할인 대기보다는 장르가 맞는지와 DLC, 배틀패스, 스킨 같은 선택 과금 구조를 확인해 주세요."
    discount = f"{game['discount_rate']}% 할인" if game["discount_rate"] else "현재 할인 없음"
    review = ""
    if game.get("steam_review_score") and game.get("steam_review_count"):
        review = f" Steam 평가는 {game['steam_review_score']}점, 리뷰 {game['steam_review_count']:,}개 기준입니다."
    return f"{game['title']}은 현재 {game['current_price']:,.0f}원이고 {discount} 상태입니다.{review} 구매 타이밍까지 보려면 게임 상세의 AI 구매 분석이 더 정확합니다."


def _chat_pick_sentence(game, rank):
    if game["current_price"] is None:
        price = "가격 정보 부족"
    elif game.get("is_free_to_play"):
        price = "기본 게임 상시 무료"
    else:
        discount = f", {game['discount_rate']}% 할인" if game["discount_rate"] else ", 현재 할인 없음"
        price = f"{game['current_price']:,.0f}원{discount}"
    genres = ", ".join(game.get("genres", [])[:2])
    genre_text = f" ({genres})" if genres else ""
    return f"{rank}. {game['title']}{genre_text}: {price}."


def _is_recommendation_question(message):
    lowered = message.lower()
    keywords = ["추천", "뭐 살", "뭘 살", "살만", "골라", "pick", "recommend"]
    return any(keyword in lowered for keyword in keywords)


def _is_bad_chat_reply(reply, context=None):
    if not reply or len(reply.strip()) < 10:
        return True
    generic_phrases = [
        "잘 이해하지 못했습니다",
        "조금 더 자세히",
        "구체적으로",
        "질문을 다시",
        "원하시는 도움",
    ]
    if any(phrase in reply for phrase in generic_phrases):
        return True
    if "\ufffd" in reply:
        return True
    if context and _mentions_unavailable_bioshock(reply, context):
        return True
    cyrillic_count = sum(1 for char in reply if "\u0400" <= char <= "\u04ff")
    if cyrillic_count >= 2:
        return True
    korean_count = sum(1 for char in reply if "\uac00" <= char <= "\ud7a3")
    if korean_count < 3:
        return True
    return False


def _mentions_unavailable_bioshock(reply, context):
    lowered = reply.lower().replace(" ", "")
    if "bioshock" not in lowered and "바이오쇼크" not in lowered:
        return False
    allowed_titles = [
        item.get("title", "")
        for item in (context.get("matched_games") or []) + (context.get("similar_discounted_games") or [])
    ]
    return not any("bioshock" in title.lower().replace(" ", "") or "바이오쇼크" in title for title in allowed_titles)


def _chat_reply_uses_disallowed_title(reply, context):
    allowed_titles = {str(game.get("title") or "").lower() for game in context.get("matched_games", [])}
    allowed_titles.update(str(title or "").lower() for title in context.get("user", {}).get("top_owned_titles", []))

    guarded_aliases = {
        "bioshock": ["bioshock", "바이오쇼크"],
        "bioShock": ["bioshock", "바이오쇼크"],
    }
    allowed_text = " ".join(allowed_titles)
    lowered_reply = (reply or "").lower()
    for title_key, aliases in guarded_aliases.items():
        title_key_lowered = title_key.lower()
        if title_key_lowered in allowed_text:
            continue
        if any(alias in lowered_reply for alias in aliases):
            return True

    candidate_titles = [title for title in allowed_titles if len(title) >= 4]
    if not candidate_titles:
        return False
    mentioned_allowed_count = sum(1 for title in candidate_titles if title in lowered_reply)
    return mentioned_allowed_count == 0


def _unique_preserve_order(items):
    result = []
    seen = set()
    for item in items:
        if item is None:
            continue
        value = str(item).strip()
        key = value.casefold()
        if value and key not in seen:
            result.append(value)
            seen.add(key)
    return result


def re_split_query(value):
    return [part.strip() for part in re.split(r"[\s,./?;:!()\[\]{}]+", value) if part.strip()]


class GmsChatError(Exception):
    pass


def _post_gms_chat_completion(base_url, api_key, model, messages, response_format=None, timeout_seconds=None):
    payload = {
        "model": model,
        "messages": messages,
    }
    if response_format:
        payload["response_format"] = response_format

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False, default=_json_safe).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds or LLM_TIMEOUT_SECONDS) as response:
            body = _read_gms_body(response)
    except urllib.error.HTTPError as exc:
        raise GmsChatError(str(exc)) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GmsChatError(str(exc)) from exc

    content = _extract_chat_content(body)
    if not content:
        raise GmsChatError("GMS response did not include assistant content.")
    return content.strip()


def _read_gms_body(response):
    try:
        raw = response.read()
    except http.client.IncompleteRead as exc:
        raw = exc.partial
    text = raw.decode("utf-8", errors="replace").strip()
    if text.startswith('"choices"'):
        text = "{" + text
    return text


def _extract_chat_content(body):
    try:
        return json.loads(body)["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        match = re.search(r'"content"\s*:\s*("(?:(?:\\.)|[^"\\])*")', body)
        if not match:
            return ""
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return ""


