<template>
  <AppLayout>
    <main class="cd-home">
      <p v-if="error" class="cd-home-error">{{ error }}</p>

      <section class="cd-hero" @mouseenter="pauseHeroAutoplay" @mouseleave="resumeHeroAutoplay">
        <div class="cd-hero-stage">
          <article
            v-for="(game, index) in heroGames"
            :key="game.id"
            class="cd-hero-card"
            :class="heroCardClass(index)"
            role="button"
            tabindex="0"
            :aria-label="heroOffset(index) === 0 ? `${game.title} 상세 보기` : `${game.title} 보기`"
            @click="handleHeroCardClick(index, game)"
            @keydown.enter.prevent="handleHeroCardClick(index, game)"
            @keydown.space.prevent="handleHeroCardClick(index, game)"
          >
            <img v-if="imageFor(game)" :src="imageFor(game)" :alt="game.title" />
            <div v-else class="cd-hero-fallback">{{ game.title?.slice(0, 2) || 'CD' }}</div>

            <div v-if="heroOffset(index) === 0" class="cd-hero-info">
              <div class="cd-hero-copy">
                <h1>{{ game.title }}</h1>
                <p>{{ genreText(game) }}</p>
              </div>
              <div class="cd-hero-price">
                <span v-if="game.max_discount" class="cd-discount">-{{ percent(game.max_discount) }}</span>
                <div>
                  <del v-if="isDiscounted(game)">{{ money(game.original_price) }}</del>
                  <strong>{{ money(game.best_price) }}</strong>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="cd-content-grid">
        <section class="cd-section cd-deals">
          <header class="cd-section-head">
            <h2>인기 할인 게임</h2>
            <router-link :to="{ path: '/games', query: { ordering: '-steam_review_count', discounted: '1' } }">더 보기</router-link>
          </header>

          <article
            v-for="game in dealList"
            :key="`${game.id}-${game.title}`"
            class="cd-deal-row"
            role="button"
            tabindex="0"
            @click="router.push(`/games/${game.id}`)"
            @keydown.enter.prevent="router.push(`/games/${game.id}`)"
            @keydown.space.prevent="router.push(`/games/${game.id}`)"
          >
            <img v-if="imageFor(game)" :src="imageFor(game)" :alt="game.title" />
            <div v-else class="cd-row-fallback">{{ game.title?.slice(0, 2) }}</div>
            <div class="cd-row-copy">
              <h3>{{ game.title }}</h3>
              <p>{{ genreText(game) }}</p>
            </div>
            <div class="cd-row-price">
              <del v-if="isDiscounted(game)">{{ money(game.original_price) }}</del>
              <span v-if="game.max_discount" class="cd-discount">-{{ percent(game.max_discount) }}</span>
              <strong>{{ money(game.best_price) }}</strong>
            </div>
          </article>

          <p v-if="!dealList.length" class="cd-empty">할인 게임 정보를 불러오는 중입니다.</p>
        </section>

        <aside class="cd-side-stack">
          <section class="cd-section">
            <header class="cd-section-head">
              <h2>지금 무료로 받기</h2>
              <router-link to="/free-games">무료 게임 전체 보기</router-link>
            </header>
            <article v-for="game in freeGamesPreview" :key="game.id || game.title" class="cd-side-row">
              <img v-if="game.thumbnail" :src="game.thumbnail" :alt="game.title" />
              <div v-else class="cd-side-fallback">{{ game.title?.slice(0, 2) }}</div>
              <div>
                <h3>{{ game.title }}</h3>
                <p>{{ game.source || 'Epic Games' }}</p>
              </div>
            </article>
            <p v-if="!freeGamesPreview.length" class="cd-empty">무료 배포 정보를 불러오지 못했습니다.</p>
          </section>

          <section class="cd-section">
            <header class="cd-section-head">
              <h2>위시리스트</h2>
              <router-link to="/wishlist">위시리스트 전체 보기</router-link>
            </header>
            <template v-for="item in wishlistPreview" :key="item.id || item.title">
              <router-link v-if="gameId(item)" class="cd-side-row cd-recommend-row" :to="`/games/${gameId(item)}`">
                <img v-if="imageFor(wishlistGame(item))" :src="imageFor(wishlistGame(item))" :alt="wishlistGame(item).title" />
                <div v-else class="cd-side-fallback">{{ wishlistGame(item).title?.slice(0, 2) }}</div>
                <div class="cd-recommend-copy">
                  <h3>{{ wishlistGame(item).title }}</h3>
                </div>
                <div class="cd-recommend-price" :class="{ 'is-discounted': isDiscounted(wishlistGame(item)) }">
                  <span v-if="isDiscounted(wishlistGame(item))" class="cd-discount">-{{ percent(wishlistGame(item).max_discount) }}</span>
                  <strong>{{ money(wishlistGame(item).best_price) }}</strong>
                </div>
              </router-link>
              <div v-else class="cd-side-row cd-recommend-row">
                <img v-if="imageFor(wishlistGame(item))" :src="imageFor(wishlistGame(item))" :alt="wishlistGame(item).title" />
                <div v-else class="cd-side-fallback">{{ wishlistGame(item).title?.slice(0, 2) }}</div>
                <div class="cd-recommend-copy">
                  <h3>{{ wishlistGame(item).title }}</h3>
                </div>
                <div class="cd-recommend-price" :class="{ 'is-discounted': isDiscounted(wishlistGame(item)) }">
                  <span v-if="isDiscounted(wishlistGame(item))" class="cd-discount">-{{ percent(wishlistGame(item).max_discount) }}</span>
                  <strong>{{ money(wishlistGame(item).best_price) }}</strong>
                </div>
              </div>
            </template>
            <p v-if="!wishlistPreview.length" class="cd-empty">아직 위시리스트에 담은 게임이 없습니다.</p>
          </section>

          <section class="cd-section cd-personalized">
            <header class="cd-section-head">
              <h2>사용자 취향 기반 추천</h2>
            </header>
            <router-link
              v-for="game in personalizedPreview"
              :key="game.id"
              class="cd-side-row cd-recommend-row"
              :to="`/games/${game.id}`"
            >
              <img v-if="imageFor(game)" :src="imageFor(game)" :alt="game.title" />
              <div v-else class="cd-side-fallback">{{ game.title?.slice(0, 2) }}</div>
              <div class="cd-recommend-copy">
                <h3>{{ game.title }}</h3>
              </div>
              <div class="cd-recommend-price" :class="{ 'is-discounted': isDiscounted(game) }">
                <span v-if="isDiscounted(game)" class="cd-discount">-{{ percent(game.max_discount) }}</span>
                <strong>{{ money(game.best_price) }}</strong>
              </div>
            </router-link>
            <p v-if="!personalizedPreview.length" class="cd-empty cd-recommend-empty">
              <span v-for="line in personalizedEmptyLines" :key="line">{{ line }}</span>
            </p>
          </section>
        </aside>
      </section>
    </main>
  </AppLayout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { gamesApi } from '../api/games'
import { recommendationsApi } from '../api/recommendations'
import { wishlistApi } from '../api/wishlist'
import AppLayout from '../layouts/AppLayout.vue'
import { money, percent } from '../utils/format'

const popular = ref([])
const router = useRouter()
const freeGames = ref([])
const wishlistItems = ref([])
const personalizedGames = ref([])
const personalizedState = ref('idle')
const activeHeroIndex = ref(0)
const heroAutoplayTimer = ref(null)
const isHeroPaused = ref(false)
const error = ref('')
const HERO_AUTOPLAY_MS = 5000
const HOME_DEAL_LIMIT = 10
const HOME_PERSONALIZED_LIMIT = 3

const heroGames = computed(() => popular.value.slice(0, 4))
const dealList = computed(() => popular.value.slice(0, HOME_DEAL_LIMIT))
const wishlistPreview = computed(() => wishlistItems.value.slice(0, 4))
const freeGamesPreview = computed(() => freeGames.value.slice(0, 4))
const personalizedPreview = computed(() => personalizedGames.value.slice(0, HOME_PERSONALIZED_LIMIT))
const personalizedEmptyLines = computed(() => {
  if (personalizedState.value === 'error') return ['취향 추천을 불러오지 못했습니다.']
  return ['Steam 계정을 연동하면', '사용자 취향에 맞는 게임 추천을 받을 수 있습니다.']
})

const isDiscounted = (game) => Number(game?.max_discount || 0) > 0 && Number(game?.original_price || 0) > Number(game?.best_price || 0)
const imageFor = (game) => game?.thumbnail || game?.hero_image || ''
const genreText = (game) => game?.genres?.map((genre) => genre.name).join(', ') || game?.platform || '액션, 어드벤처'
const wishlistGame = (item) => item?.game || item || {}
const gameId = (item) => item.game?.id || item.game_id || null

const heroOffset = (index) => {
  const length = heroGames.value.length
  if (!length) return 0
  let offset = (index - activeHeroIndex.value + length) % length
  if (offset > length / 2) offset -= length
  return offset
}

const heroCardClass = (index) => {
  const offset = heroOffset(index)
  return {
    'cd-hero-card-main': offset === 0,
    'cd-hero-card-left': offset === -1,
    'cd-hero-card-right': offset === 1,
    'cd-hero-card-hidden': Math.abs(offset) > 1,
  }
}

const handleHeroCardClick = (index, game) => {
  if (heroOffset(index) === 0) {
    router.push(`/games/${game.id}`)
    return
  }
  activeHeroIndex.value = index
  resetHeroAutoplay()
}

const nextHero = () => {
  if (heroGames.value.length <= 1) return
  activeHeroIndex.value = (activeHeroIndex.value + 1) % heroGames.value.length
  resetHeroAutoplay()
}

const prevHero = () => {
  if (heroGames.value.length <= 1) return
  activeHeroIndex.value = (activeHeroIndex.value - 1 + heroGames.value.length) % heroGames.value.length
  resetHeroAutoplay()
}

const advanceHero = () => {
  if (heroGames.value.length <= 1) return
  activeHeroIndex.value = (activeHeroIndex.value + 1) % heroGames.value.length
}

const stopHeroAutoplay = () => {
  if (!heroAutoplayTimer.value) return
  window.clearInterval(heroAutoplayTimer.value)
  heroAutoplayTimer.value = null
}

const startHeroAutoplay = () => {
  stopHeroAutoplay()
  if (isHeroPaused.value || heroGames.value.length <= 1) return
  heroAutoplayTimer.value = window.setInterval(advanceHero, HERO_AUTOPLAY_MS)
}

const resetHeroAutoplay = () => {
  startHeroAutoplay()
}

const pauseHeroAutoplay = () => {
  isHeroPaused.value = true
  stopHeroAutoplay()
}

const resumeHeroAutoplay = () => {
  isHeroPaused.value = false
  startHeroAutoplay()
}

watch(heroGames, (games) => {
  if (!games.length) {
    activeHeroIndex.value = 0
    stopHeroAutoplay()
    return
  }
  activeHeroIndex.value %= games.length
  startHeroAutoplay()
})

onMounted(async () => {
  const [popularResult, freeResult, wishlistResult, personalizedResult] = await Promise.allSettled([
    gamesApi.popularDiscounts(HOME_DEAL_LIMIT),
    gamesApi.epicFree(),
    wishlistApi.list(),
    recommendationsApi.homePersonalized(HOME_PERSONALIZED_LIMIT),
  ])
  if (popularResult.status === 'fulfilled') popular.value = popularResult.value
  if (freeResult.status === 'fulfilled') freeGames.value = freeResult.value
  if (wishlistResult.status === 'fulfilled') wishlistItems.value = wishlistResult.value
  if (personalizedResult.status === 'fulfilled') {
    personalizedGames.value = personalizedResult.value?.items || []
    personalizedState.value = personalizedGames.value.length ? 'ready' : 'connect'
  } else {
    personalizedState.value = [401, 403].includes(personalizedResult.reason?.status) ? 'connect' : 'error'
  }
  const failed = [popularResult, freeResult].find((result) => result.status === 'rejected')
  if (failed) error.value = failed.reason?.message || '데이터를 불러오지 못했습니다.'
})

onBeforeUnmount(stopHeroAutoplay)
</script>

<style scoped>
.cd-home {
  --cd-page: #191919;
  --cd-surface: #1f1f1f;
  --cd-surface-elevated: #252525;
  --cd-border: #333333;
  --cd-text: #d9d9d8;
  --cd-muted: #a3a3a2;
  --cd-hover: #252525;
  --cd-fallback-bg: #202020;
  --cd-fallback-text: #3183d8;

  width: min(100%, 1180px);
  margin: 0 auto;
  padding-bottom: 28px;
  color: var(--cd-text);
}

:global(:root[data-theme="light"]) .cd-home {
  --cd-page: #ffffff;
  --cd-surface: #ffffff;
  --cd-surface-elevated: #f8fafc;
  --cd-border: #d8dde6;
  --cd-text: #111827;
  --cd-muted: #4b5563;
  --cd-hover: #f8fafc;
  --cd-fallback-bg: #dbeafe;
  --cd-fallback-text: #1d4ed8;
}

.cd-home-error {
  margin: 12px 0;
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #b42318;
  padding: 12px 14px;
}

.cd-hero {
  position: relative;
  height: 510px;
  overflow: hidden;
  padding-top: 24px;
}

.cd-hero-stage {
  position: relative;
  width: min(100%, 1160px);
  height: 456px;
  margin: 0 auto;
  perspective: 1200px;
}

.cd-hero-card {
  position: absolute;
  top: 18px;
  left: 50%;
  overflow: hidden;
  width: min(880px, 78vw);
  height: 420px;
  border-radius: 8px;
  background: #151515;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 0.46s ease,
    transform 0.58s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.46s ease,
    box-shadow 0.46s ease;
  will-change: transform, opacity;
}

.cd-hero-card img,
.cd-hero-fallback {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.cd-hero-card img {
  object-fit: cover;
}

.cd-hero-fallback {
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
  color: #ffffff;
  font-size: 52px;
  font-weight: 900;
}

.cd-hero-card-main {
  z-index: 3;
  opacity: 1;
  pointer-events: auto;
  transform: translateX(-50%) translateZ(0) scale(1);
  box-shadow: 0 24px 54px rgba(0, 0, 0, 0.42);
}

.cd-hero-card-left {
  z-index: 2;
  opacity: 0.72;
  pointer-events: auto;
  transform: translateX(calc(-50% - 360px)) translateY(34px) scale(0.78);
  filter: saturate(0.78) brightness(0.82);
}

.cd-hero-card-right {
  z-index: 2;
  opacity: 0.72;
  pointer-events: auto;
  transform: translateX(calc(-50% + 360px)) translateY(34px) scale(0.78);
  filter: saturate(0.78) brightness(0.82);
}

.cd-hero-card-hidden {
  z-index: 0;
  opacity: 0;
  transform: translateX(-50%) translateY(48px) scale(0.62);
}

.cd-hero-card-main:hover {
  transform: translateX(-50%) translateY(-3px) scale(1.01);
  box-shadow: 0 30px 68px rgba(0, 0, 0, 0.4);
}

.cd-hero-card-left:hover,
.cd-hero-card-right:hover {
  opacity: 0.88;
  filter: saturate(0.9) brightness(0.94);
}

.cd-hero-card-main::before {
  position: absolute;
  inset: 0;
  z-index: 1;
  content: "";
  background:
    linear-gradient(180deg, rgba(3, 7, 18, 0) 32%, rgba(3, 7, 18, 0.22) 58%, rgba(3, 7, 18, 0.82) 100%),
    linear-gradient(90deg, rgba(3, 7, 18, 0.32), rgba(3, 7, 18, 0) 52%);
}

.cd-hero-info {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 22px;
  align-items: end;
  min-height: 154px;
  padding: 28px 30px 30px;
}

.cd-hero-copy {
  min-width: 0;
}

.cd-hero-copy h1 {
  margin: 0 0 9px;
  overflow: hidden;
  color: #ffffff;
  font-size: 52px;
  font-weight: 900;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cd-hero-copy p {
  margin: 0;
  overflow: hidden;
  color: rgba(255, 255, 255, 0.9);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cd-hero-price {
  display: grid;
  justify-items: end;
  gap: 8px;
  min-width: 196px;
}

.cd-hero-price > div {
  display: flex;
  align-items: end;
  gap: 8px;
}

.cd-hero-price del {
  color: #ffffff;
  font-size: 24px;
  font-weight: 900;
}

.cd-hero-price strong {
  color: #ff1834 !important;
  font-size: 34px;
  font-weight: 900;
  line-height: 1;
}

.cd-discount {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 66px;
  background: #e60023;
  color: #ffffff;
  padding: 7px 8px;
  font-size: 20px;
  font-weight: 900;
  line-height: 1;
}

.cd-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 430px;
  gap: 18px;
  margin-top: 18px;
}

.cd-section {
  border: 0;
  background: var(--cd-page);
}

.cd-deals {
  width: 100%;
}

.cd-section-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 13px 14px 11px;
}

.cd-section-head h2 {
  margin: 0;
  color: var(--cd-text);
  font-size: 17px;
  font-weight: 900;
}

.cd-section-head a {
  color: var(--cd-muted);
  font-size: 12px;
  text-decoration: underline;
  text-underline-offset: 2px;
  white-space: nowrap;
}

.cd-deal-row,
.cd-side-row {
  display: grid;
  align-items: center;
  border-top: 1px solid var(--cd-border);
  color: inherit;
  text-decoration: none;
}

.cd-deal-row {
  grid-template-columns: 184px minmax(0, 1fr) 118px;
  min-height: 74px;
  cursor: pointer;
}

.cd-deal-row:hover,
.cd-side-row:hover {
  background: var(--cd-hover);
}

.cd-deal-row img,
.cd-row-fallback {
  width: 184px;
  height: 74px;
}

.cd-deal-row img,
.cd-side-row img {
  object-fit: cover;
}

.cd-row-fallback,
.cd-side-fallback {
  display: grid;
  place-items: center;
  background: var(--cd-fallback-bg);
  color: var(--cd-fallback-text);
  font-weight: 900;
}

.cd-row-copy {
  min-width: 0;
  padding: 0 10px;
}

.cd-row-copy h3,
.cd-side-row h3 {
  margin: 0 0 5px;
  overflow: hidden;
  color: var(--cd-text);
  font-size: 14px;
  font-weight: 900;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cd-row-copy p,
.cd-side-row p {
  margin: 0;
  overflow: hidden;
  color: var(--cd-muted);
  font-size: 11px;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cd-row-price {
  display: grid;
  grid-template-columns: auto auto;
  justify-content: end;
  justify-items: end;
  align-items: center;
  gap: 4px 6px;
  padding-right: 14px;
}

.cd-row-price del {
  grid-column: 2;
  grid-row: 1;
  justify-self: end;
  color: var(--cd-muted);
  font-size: 11px;
  font-weight: 900;
  line-height: 1;
}

.cd-row-price .cd-discount {
  grid-column: 1;
  grid-row: 2;
  align-self: center;
  transform: translateY(2px);
  min-width: 38px;
  padding: 3px 5px;
  font-size: 11px;
}

.cd-row-price strong {
  grid-column: 2;
  grid-row: 2;
  justify-self: end;
  color: #ff1834 !important;
  font-size: 17px;
  font-weight: 900;
  line-height: 1;
}

.cd-side-stack {
  display: grid;
  gap: 12px;
  align-content: start;
  border-left: 1px solid var(--cd-border);
  padding-left: 18px;
}

.cd-side-row {
  grid-template-columns: 126px minmax(0, 1fr);
  min-height: 62px;
  gap: 9px;
  padding-right: 10px;
}

.cd-side-row img,
.cd-side-fallback {
  width: 126px;
  height: 62px;
}

.cd-recommend-row {
  grid-template-columns: 118px minmax(0, 1fr) 76px;
  min-height: 68px;
  gap: 10px;
}

.cd-recommend-row img,
.cd-recommend-row .cd-side-fallback {
  width: 118px;
  height: 68px;
  align-self: stretch;
}

.cd-recommend-copy {
  min-width: 0;
}

.cd-recommend-copy h3 {
  margin-bottom: 0;
}

.cd-recommend-price {
  display: grid;
  justify-items: end;
  gap: 4px;
  padding-right: 2px;
}

.cd-recommend-price .cd-discount {
  min-width: 38px;
  padding: 3px 5px;
  font-size: 11px;
}

.cd-recommend-price strong {
  color: var(--cd-text) !important;
  font-size: 14px;
  font-weight: 900;
  line-height: 1;
  white-space: nowrap;
}

.cd-recommend-price.is-discounted strong {
  color: #ff1834 !important;
}

.cd-recommend-empty {
  display: grid;
  gap: 4px;
  line-height: 1.45;
}

.cd-empty {
  margin: 0;
  border-top: 1px solid var(--cd-border);
  color: var(--cd-muted);
  padding: 14px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .cd-content-grid {
    grid-template-columns: 1fr;
  }

  .cd-side-stack {
    border-left: 0;
    padding-left: 0;
  }
}

@media (max-width: 720px) {
  .cd-hero {
    height: 340px;
    padding-top: 18px;
  }

  .cd-hero-stage {
    height: 300px;
  }

  .cd-hero-card {
    top: 12px;
    width: 84vw;
    height: 276px;
  }

  .cd-hero-card-main {
    transform: translateX(-50%) scale(1);
  }

  .cd-hero-card-left {
    transform: translateX(calc(-50% - 44vw)) translateY(24px) scale(0.72);
  }

  .cd-hero-card-right {
    transform: translateX(calc(-50% + 44vw)) translateY(24px) scale(0.72);
  }

  .cd-hero-card-main:hover {
    transform: translateX(-50%) scale(1);
  }

  .cd-hero-info {
    grid-template-columns: 1fr;
    gap: 8px;
    min-height: 116px;
    padding: 16px;
  }

  .cd-hero-copy h1 {
    font-size: 30px;
  }

  .cd-hero-copy p {
    font-size: 12px;
  }

  .cd-hero-price {
    justify-items: start;
    min-width: 108px;
  }

  .cd-hero-price del {
    font-size: 12px;
  }

  .cd-hero-price strong {
    font-size: 19px;
  }

  .cd-discount {
    min-width: 40px;
    padding: 3px 5px;
    font-size: 12px;
  }

  .cd-deal-row {
    grid-template-columns: 110px minmax(0, 1fr) 92px;
    min-height: 66px;
  }

  .cd-deal-row img,
  .cd-row-fallback {
    width: 110px;
    height: 66px;
  }

  .cd-row-copy h3 {
    font-size: 13px;
  }

  .cd-row-price strong {
    font-size: 14px;
  }
}
</style>
