import json
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import UserGame, UserSteamAccount
from games.models import Game, GameComment, GameCommentReaction


USER_PREFIX = "dummy_comm_"
USER_COUNT = 96
PASSWORD = "Dummy!2026"
RANDOM_SEED = 20260625

PRIMARY_GAMES = [
    {"id": 310, "label": "데이브 더 다이버", "key": "dave", "top": 58, "replies": 34},
    {"id": 358, "label": "돈스타브", "key": "dont_starve", "top": 58, "replies": 34},
    {"id": 54, "label": "Don't Starve Together", "key": "dont_starve", "top": 58, "replies": 34},
    {"id": 2692, "label": "사이버 펑크", "key": "cyberpunk", "top": 58, "replies": 34},
]

EXTRA_GAMES = [
    {"id": 2694, "label": "ELDEN RING", "key": "elden_ring", "top": 22, "replies": 14},
    {"id": 2675, "label": "Stardew Valley", "key": "stardew", "top": 22, "replies": 14},
    {"id": 41, "label": "Garry's Mod", "key": "garrys_mod", "top": 22, "replies": 14},
    {"id": 62, "label": "Black Myth: Wukong", "key": "wukong", "top": 22, "replies": 14},
    {"id": 2693, "label": "Red Dead Redemption 2", "key": "rdr2", "top": 22, "replies": 14},
]

PERSONAS = [
    "할인헌터",
    "밤샘게이머",
    "찐스팀러",
    "장바구니요정",
    "가격추적자",
    "패드장인",
    "도전과제러",
    "세일대기중",
    "인디수집가",
    "리뷰읽는사람",
    "겜잘알희망편",
    "라이브러리부자",
    "초보모험가",
    "도트취향",
    "오픈월드러",
    "보스전무서움",
]

GAME_COMMENTS = {
    "dave": [
        "낮에는 다이빙하고 밤에는 초밥집 굴리는 루프가 생각보다 중독적이에요.",
        "초반은 힐링인데 손님 몰리기 시작하면 은근 바빠서 손맛이 있습니다.",
        "물고기 잡는 재미랑 장비 업그레이드가 잘 맞물려서 계속 한 판만 더 하게 됩니다.",
        "보스전이 뜬금없을 때도 있는데 전체 분위기가 좋아서 넘어가게 돼요.",
        "도트 그래픽인데 바닷속 표현이 좋아서 스샷 찍는 맛도 있어요.",
        "가격 할인할 때 사면 만족도는 거의 보장이라고 봅니다.",
        "스토리 템포가 가볍고 캐릭터들이 귀여워서 부담 없이 하기 좋아요.",
        "운영 파트가 반복적일 줄 알았는데 메뉴 연구 때문에 계속 붙잡게 됩니다.",
        "다이빙 조작은 초반에 살짝 답답한데 장비 맞추면 확 좋아져요.",
        "힐링 게임인 줄 알고 샀다가 경영 게임으로 밤새웠습니다.",
    ],
    "dont_starve": [
        "겨울 대비 못 하면 바로 망하는데 그 긴장감 때문에 계속 하게 돼요.",
        "처음엔 너무 불친절한데 한 번 생존 루틴 잡히면 재미가 확 올라옵니다.",
        "굶지마 특유의 그림체랑 분위기는 지금 봐도 대체가 없어요.",
        "실패하면서 배우는 게임이라 공략 안 보면 초반 진입장벽은 있습니다.",
        "계절 넘어갈 때마다 준비물 체크하는 맛이 좋아요.",
        "솔로로 천천히 배워도 재밌고 친구랑 하면 훨씬 정신없습니다.",
        "음식 관리랑 정신력 관리가 은근 빡세서 취향 많이 탈 것 같아요.",
        "할인 자주 하니까 생존 게임 좋아하면 사둘 만합니다.",
        "초보는 첫 목표를 겨울 넘기기로 잡으면 괜찮아요.",
        "불친절함까지 매력인 게임인데 그게 스트레스인 사람도 있을 듯합니다.",
    ],
    "cyberpunk": [
        "2.0 이후로 전투랑 성장 쪽이 훨씬 좋아져서 지금은 추천할 만해요.",
        "나이트시티 분위기는 아직도 독보적이라 돌아다니기만 해도 좋습니다.",
        "스토리는 몰입감 좋은데 사이드 퀘스트까지 해야 진짜 맛이 나요.",
        "출시 초반 이미지 때문에 망설였는데 지금 플레이하면 꽤 탄탄합니다.",
        "총기 빌드보다 넷러너 빌드가 취향이라면 더 재밌게 할 수 있어요.",
        "사양은 여전히 좀 먹지만 그래픽 옵션 맞추면 충분히 즐길 만합니다.",
        "팬텀 리버티까지 같이 하면 완성도가 확 올라가는 느낌이에요.",
        "할인율 높을 때 본편 먼저 사보고 DLC는 나중에 붙여도 좋습니다.",
        "버그가 아예 없는 건 아닌데 예전처럼 진행 막힐 정도는 아니었습니다.",
        "도시 분위기와 음악 때문에 엔딩 보고도 가끔 다시 켜게 됩니다.",
    ],
    "elden_ring": [
        "초반 진입은 빡센데 맵 탐험이 압도적이라 계속 길을 벗어나게 됩니다.",
        "보스 패턴 익히고 잡는 순간의 쾌감은 여전히 최고예요.",
        "오픈월드랑 소울류가 이렇게 잘 맞을 줄 몰랐습니다.",
        "공략 없이 하면 놓치는 게 많지만 그만큼 발견하는 재미가 있어요.",
        "어려워도 빌드 바꾸면 길이 열리는 구조라 생각보다 친절한 편입니다.",
    ],
    "stardew": [
        "농사만 하려다가 낚시하고 광산 가고 주민 선물 챙기느라 시간이 사라집니다.",
        "느긋하게 해도 되고 효율 따져도 되는 점이 정말 좋아요.",
        "멀티로 하면 역할 나눠서 농장 키우는 재미가 꽤 큽니다.",
        "할인 안 해도 값어치 충분한데 할인하면 그냥 사도 됩니다.",
        "힐링 게임인데 은근히 하루 계획 세우는 맛이 있습니다.",
    ],
    "garrys_mod": [
        "샌드박스 좋아하면 아직도 할 게 많은 게임입니다.",
        "모드 서버마다 완전히 다른 게임처럼 느껴져서 수명이 길어요.",
        "친구들이랑 장난치기 좋은데 혼자 하면 목적이 애매할 수 있습니다.",
        "가격이 낮아서 라이브러리에 넣어두면 언젠가 쓰게 됩니다.",
        "커뮤니티 콘텐츠가 핵심이라 서버 고르는 게 제일 중요해요.",
    ],
    "wukong": [
        "연출이 좋아서 보스전 들어갈 때마다 기대하게 됩니다.",
        "전투 리듬이 빠른 편이라 패턴 보는 맛이 있어요.",
        "그래픽과 분위기는 확실히 강점인데 사양 체크는 필요합니다.",
        "액션 게임 좋아하면 할인 때 노려볼 만합니다.",
        "보스 난이도가 구간마다 튀어서 호불호는 있을 것 같아요.",
    ],
    "rdr2": [
        "느린 템포만 맞으면 몰입감은 정말 대단합니다.",
        "서부 분위기와 디테일 때문에 산책만 해도 시간이 갑니다.",
        "초반이 길어서 답답할 수 있지만 이후 서사가 크게 터집니다.",
        "할인하면 무조건 추천할 만한 싱글 게임입니다.",
        "조작감은 묵직한데 그게 세계관이랑 잘 맞아요.",
    ],
}

REPLY_TEMPLATES = [
    "저도 이 부분 공감해요. 초반만 넘기면 확 재밌어지더라고요.",
    "맞아요. 할인 기준으로 보면 만족도가 꽤 좋은 편입니다.",
    "저는 반대로 그 지점이 조금 아쉬웠는데 그래도 전체적으로는 괜찮았어요.",
    "처음 하는 분이면 이 댓글 보고 세팅부터 챙기면 좋을 듯합니다.",
    "플레이타임 어느 정도 쌓이면 장점이 더 잘 보이는 게임 같아요.",
    "친구랑 같이 하면 체감이 완전히 달라지는 부분도 있습니다.",
    "이거 때문에 저도 다시 설치했습니다.",
    "취향만 맞으면 가격 대비 오래 즐길 수 있어요.",
    "공략 조금만 보고 시작하면 스트레스가 훨씬 줄어듭니다.",
    "저도 비슷하게 느꼈어요. 단점은 있는데 매력이 더 큽니다.",
]


def get_game(game_info):
    try:
        return Game.objects.get(pk=game_info["id"])
    except Game.DoesNotExist:
        return Game.objects.filter(title__icontains=game_info["label"]).first()


def create_users():
    User = get_user_model()
    existing = User.objects.filter(username__startswith=USER_PREFIX)
    deleted_count = existing.count()
    existing.delete()

    users = []
    for index in range(1, USER_COUNT + 1):
        username = f"{USER_PREFIX}{index:03d}"
        user = User.objects.create_user(
            username=username,
            email=f"{username}@criticaldeal.test",
            password=PASSWORD,
        )
        persona = f"{PERSONAS[(index - 1) % len(PERSONAS)]}{index:02d}"
        UserSteamAccount.objects.create(
            user=user,
            steam_id=f"76561199{index:09d}",
            persona_name=persona,
            profile_url=f"https://steamcommunity.com/id/{username}",
            avatar_url="",
        )
        users.append(user)
    return deleted_count, users


def assign_playtime(users, games):
    rows = []
    for user in users:
        for game in games:
            if random.random() < 0.86:
                rows.append(
                    UserGame(
                        user=user,
                        game=game,
                        source="steam",
                        playtime_minutes=random.randint(70, 18000),
                    )
                )
    UserGame.objects.bulk_create(rows, ignore_conflicts=True)


def comment_text(game_key, index):
    pool = GAME_COMMENTS.get(game_key) or GAME_COMMENTS["stardew"]
    base = pool[index % len(pool)]
    suffixes = [
        "최근 할인 기준으로도 꽤 괜찮은 선택이라고 봅니다.",
        "개인적으로는 한두 시간 지나고 나서 재미가 붙었어요.",
        "처음엔 애매했는데 시스템 이해하고 나니 평가가 올라갔습니다.",
        "완성도보다 취향 영향이 큰 게임이라 영상 한 번 보고 사는 걸 추천합니다.",
        "세일 폭이 크면 친구한테도 권할 수 있을 정도예요.",
        "짧게 하려다가 주말이 사라졌습니다.",
    ]
    return f"{base} {suffixes[(index // len(pool)) % len(suffixes)]}"


def reply_text(index):
    return REPLY_TEMPLATES[index % len(REPLY_TEMPLATES)]


def set_comment_time(comment, days_back, minutes_back, edited=False):
    created_at = timezone.now() - timedelta(days=days_back, minutes=minutes_back)
    updated_at = created_at + timedelta(minutes=random.randint(15, 360)) if edited else created_at
    GameComment.objects.filter(pk=comment.pk).update(created_at=created_at, updated_at=updated_at)
    comment.created_at = created_at
    comment.updated_at = updated_at


def reaction_targets(comment_index, is_reply=False):
    if is_reply:
        likes = random.randint(0, 12)
        dislikes = random.randint(0, 4)
    elif comment_index < 4:
        likes = random.randint(34, 68)
        dislikes = random.randint(0, 8)
    elif comment_index < 10:
        likes = random.randint(18, 42)
        dislikes = random.randint(1, 12)
    elif comment_index % 13 == 0:
        likes = random.randint(8, 22)
        dislikes = random.randint(10, 28)
    else:
        likes = random.randint(1, 18)
        dislikes = random.randint(0, 9)
    return likes, dislikes


def add_reactions(comment, users, likes, dislikes):
    eligible = [user for user in users if user.id != comment.user_id]
    random.shuffle(eligible)
    likes = min(likes, len(eligible))
    dislikes = min(dislikes, max(0, len(eligible) - likes))
    rows = [
        GameCommentReaction(comment=comment, user=user, value=GameCommentReaction.LIKE)
        for user in eligible[:likes]
    ]
    rows.extend(
        GameCommentReaction(comment=comment, user=user, value=GameCommentReaction.DISLIKE)
        for user in eligible[likes : likes + dislikes]
    )
    GameCommentReaction.objects.bulk_create(rows, ignore_conflicts=True)
    return likes, dislikes


def seed_game(game_info, game, users):
    top_comments = []
    created_comments = []
    reaction_total = {"likes": 0, "dislikes": 0}

    for index in range(game_info["top"]):
        user = users[(index * 7 + game.id) % len(users)]
        comment = GameComment.objects.create(
            game=game,
            user=user,
            content=comment_text(game_info["key"], index),
        )
        set_comment_time(comment, random.randint(1, 55), random.randint(0, 1440), edited=random.random() < 0.18)
        likes, dislikes = reaction_targets(index)
        added_likes, added_dislikes = add_reactions(comment, users, likes, dislikes)
        reaction_total["likes"] += added_likes
        reaction_total["dislikes"] += added_dislikes
        top_comments.append(comment)
        created_comments.append(comment)

    for index in range(game_info["replies"]):
        parent = top_comments[index % len(top_comments)]
        user = users[(index * 11 + game.id + 3) % len(users)]
        if user.id == parent.user_id:
            user = users[(users.index(user) + 1) % len(users)]
        reply = GameComment.objects.create(
            game=game,
            user=user,
            parent=parent,
            content=reply_text(index),
        )
        set_comment_time(reply, random.randint(0, 40), random.randint(0, 1440), edited=random.random() < 0.12)
        likes, dislikes = reaction_targets(index, is_reply=True)
        added_likes, added_dislikes = add_reactions(reply, users, likes, dislikes)
        reaction_total["likes"] += added_likes
        reaction_total["dislikes"] += added_dislikes
        created_comments.append(reply)

    return {
        "id": game.id,
        "title": game.title,
        "top_level_comments": game_info["top"],
        "replies": game_info["replies"],
        "total_comments": len(created_comments),
        "likes": reaction_total["likes"],
        "dislikes": reaction_total["dislikes"],
    }


@transaction.atomic
def run():
    random.seed(RANDOM_SEED)
    deleted_users, users = create_users()
    game_infos = PRIMARY_GAMES + EXTRA_GAMES
    games = []
    for game_info in game_infos:
        game = get_game(game_info)
        if not game:
            raise RuntimeError(f"Game not found: {game_info['label']}")
        games.append(game)

    assign_playtime(users, games)
    game_summaries = []
    for game_info, game in zip(game_infos, games):
        game_summaries.append(seed_game(game_info, game, users))

    summary = {
        "deleted_previous_dummy_users": deleted_users,
        "created_dummy_users": len(users),
        "username_range": f"{USER_PREFIX}001 ~ {USER_PREFIX}{USER_COUNT:03d}",
        "email_pattern": f"{USER_PREFIX}{{001..{USER_COUNT:03d}}}@criticaldeal.test",
        "password": PASSWORD,
        "games": game_summaries,
        "total_comments": sum(item["total_comments"] for item in game_summaries),
        "total_likes": sum(item["likes"] for item in game_summaries),
        "total_dislikes": sum(item["dislikes"] for item in game_summaries),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


run()
