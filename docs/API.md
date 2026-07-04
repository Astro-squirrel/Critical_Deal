# Critical Deal API

공통 응답 형식:

```json
{
  "success": true,
  "message": "ok",
  "data": {}
}
```

## Accounts

| Method | URL | 설명 |
| --- | --- | --- |
| POST | `/api/accounts/signup/` | 이메일, 비밀번호로 회원가입 |
| POST | `/api/accounts/login/` | 이메일 로그인 |
| POST | `/api/accounts/logout/` | 세션 로그아웃 |
| GET | `/api/accounts/me/` | 현재 사용자 |
| POST | `/api/accounts/steam/connect/` | Steam ID 또는 프로필 URL 연동 |

## Games

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/games/search/?q=` | 게임명/장르 검색 |
| GET | `/api/games/` | 필터, 정렬, 페이지네이션 게임 목록 |
| GET | `/api/games/:id/` | 게임 상세 |
| GET | `/api/games/:id/prices/` | 플랫폼별 가격 |
| GET | `/api/games/:id/history/` | 가격 히스토리 |
| GET | `/api/games/:id/recommendation/` | AI 구매 추천 점수와 설명 |

## Deals

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/deals/popular/` | 인기 할인 게임 |
| GET | `/api/deals/best/` | 할인율이 높은 게임 |
| GET | `/api/epic/free-games/` | Epic 무료 게임 |

## Wishlist and Recommendations

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/wishlist/` | 내 찜 목록 |
| POST | `/api/wishlist/` | 찜 추가, body: `{ "game_id": 1 }` |
| DELETE | `/api/wishlist/:id/` | 찜 삭제 |
| GET | `/api/recommendations/personalized/` | Steam 보유 게임/장르 기반 개인화 추천 |

