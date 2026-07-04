<template>
  <AppLayout>
    <div class="explore-page-shell" :class="{ 'popular-deals-mode': isPopularDealsView }">
      <aside v-if="!isPopularDealsView" class="filter-popover explore-filter-sidebar">
        <header class="filter-popover-header">
          <h2>필터</h2>
        </header>

        <div class="filter-popover-body filter-accordion">
          <section class="filter-accordion-item" :class="{ open: activeTab === 'deals' }">
            <button
              type="button"
              class="filter-tab filter-accordion-trigger"
              :class="{ active: activeTab === 'deals' }"
              :aria-expanded="activeTab === 'deals'"
              @click="toggleFilterSection('deals')"
            >
              <Tag :size="18" />
              <span>가격</span>
              <ChevronDown :size="18" />
            </button>
            <Transition name="filter-accordion-slide">
              <div v-if="activeTab === 'deals'" class="filter-accordion-panel filter-stack">
                <div class="filter-section">
                  <h3>현재 가격</h3>
                  <div class="quick-options preset-row price-preset-row">
                    <button
                      v-for="price in pricePresets"
                      :key="price.value"
                      type="button"
                      :class="{ active: String(draft.max_price) === price.value }"
                      @click="draft.max_price = price.value"
                    >
                      {{ price.label }}
                    </button>
                  </div>
                  <div class="slider-field">
                    <input v-model="draft.max_price" type="range" min="0" max="80000" step="5000" />
                    <strong class="slider-current-value">{{ priceLabel(draft.max_price) }}</strong>
                  </div>
                </div>

                <div class="filter-section">
                  <h3>할인율</h3>
                  <div class="quick-options preset-row discount-preset-row">
                    <button
                      v-for="cut in discountPresets"
                      :key="cut.value"
                      type="button"
                      :class="{ active: String(draft.discount) === cut.value }"
                      @click="draft.discount = cut.value"
                    >
                      {{ cut.label }}
                    </button>
                  </div>
                  <div class="slider-field">
                    <input v-model="draft.discount" type="range" min="0" max="100" step="5" />
                    <strong class="slider-current-value">-{{ draft.discount || 0 }}%</strong>
                  </div>
                </div>
              </div>
            </Transition>
          </section>

          <section class="filter-accordion-item" :class="{ open: activeTab === 'genre' }">
            <button
              type="button"
              class="filter-tab filter-accordion-trigger"
              :class="{ active: activeTab === 'genre' }"
              :aria-expanded="activeTab === 'genre'"
              @click="toggleFilterSection('genre')"
            >
              <Gamepad2 :size="18" />
              <span>장르</span>
              <ChevronDown :size="18" />
            </button>
            <Transition name="filter-accordion-slide">
              <div v-if="activeTab === 'genre'" class="filter-accordion-panel filter-section">
                <h3>장르</h3>
                <div class="modal-genre-grid">
                  <label v-for="genre in genres" :key="genre" class="genre-check">
                    <input v-model="draft.genres" type="checkbox" :value="genre" />
                    <span>{{ genre }}</span>
                  </label>
                </div>
              </div>
            </Transition>
          </section>

          <section class="filter-accordion-item" :class="{ open: activeTab === 'reviews' }">
            <button
              type="button"
              class="filter-tab filter-accordion-trigger"
              :class="{ active: activeTab === 'reviews' }"
              :aria-expanded="activeTab === 'reviews'"
              @click="toggleFilterSection('reviews')"
            >
              <ThumbsUp :size="18" />
              <span>평가</span>
              <ChevronDown :size="18" />
            </button>
            <Transition name="filter-accordion-slide">
              <div v-if="activeTab === 'reviews'" class="filter-accordion-panel filter-stack">
                <div class="filter-section">
                  <h3>Steam 평가</h3>
                  <div class="quick-options preset-row review-preset-row">
                    <button
                      v-for="review in reviewPresets"
                      :key="review.value"
                      type="button"
                      :class="{ active: String(draft.review_score) === review.value }"
                      @click="draft.review_score = review.value"
                    >
                      {{ review.label }}
                    </button>
                  </div>
                  <div class="slider-field">
                    <input
                      :value="reviewScoreToSlider(draft.review_score)"
                      type="range"
                      min="0"
                      max="4"
                      step="1"
                      @input="draft.review_score = reviewSliderToScore($event.target.value)"
                    />
                    <strong class="slider-current-value">{{ reviewScoreLabel(draft.review_score) }}</strong>
                  </div>
                </div>
                <div class="filter-section">
                  <h3>리뷰 수</h3>
                  <div class="slider-field">
                    <input v-model="draft.review_count" type="range" min="0" max="100000" step="1000" />
                    <strong class="slider-current-value">{{ reviewCountLabel(draft.review_count) }}</strong>
                  </div>
                </div>
              </div>
            </Transition>
          </section>

        </div>

        <div class="filter-inline-toggle dlc-filter-footer">
          <div>
            <h3>DLC 표기</h3>
          </div>
          <span
            class="dlc-switch"
            :class="{ on: isDlcIncluded(draft.include_dlc) }"
            role="switch"
            :aria-pressed="isDlcIncluded(draft.include_dlc)"
            :aria-checked="isDlcIncluded(draft.include_dlc)"
            tabindex="0"
            @click="toggleDlcDisplay"
            @keydown.enter.prevent="toggleDlcDisplay"
            @keydown.space.prevent="toggleDlcDisplay"
          >
            <i aria-hidden="true"></i>
          </span>
        </div>
      </aside>

      <div class="explore-results-pane">
        <section v-if="isPopularDealsView" class="panel list-header popular-deals-header">
          <h1>인기 할인</h1>
        </section>
        <section v-if="!isPopularDealsView" class="explore-topbar">
          <label class="explore-search">
            <Search :size="22" />
            <input v-model="filters.q" placeholder="게임 검색" @keyup.enter="applyFilters" />
          </label>
          <label class="explore-sort">
            <span>정렬</span>
            <select v-model="filters.ordering" @change="applyFilters">
              <option value="-steam_review_count">인기순</option>
              <option value="-max_discount">할인율 높은순</option>
              <option value="best_price">낮은 가격순</option>
              <option value="title">이름순</option>
            </select>
          </label>
        </section>

        <LoadingSpinner v-if="loading" />
        <section v-else class="explore-list">
          <article v-for="game in games" :key="game.id" class="explore-row" @click="goToGame(game.id)">
            <GameImage :src="game.thumbnail || game.hero_image" :alt="game.title" :steam-app-id="game.steam_app_id" />
            <div class="explore-copy">
              <h2>{{ game.title }}</h2>
              <p>{{ genreText(game) }}</p>
            </div>
            <div class="explore-price" :class="{ discounted: isDiscounted(game) }">
              <span v-if="isDiscounted(game)" class="discount">-{{ percent(game.max_discount) }}</span>
              <div>
                <del v-if="isDiscounted(game)">{{ money(game.original_price) }}</del>
                <strong>{{ money(game.best_price) }}</strong>
              </div>
            </div>
          </article>

          <p v-if="!games.length" class="profile-empty">조건에 맞는 게임이 없습니다.</p>
          <div v-else-if="totalPages > 1" class="pagination-bar" aria-label="페이지 선택">
            <button
              v-if="hasLeadingEllipsis"
              type="button"
              class="pagination-jump"
              aria-label="첫 페이지"
              @click="changePage(1)"
            >
              …
            </button>
            <button
              v-for="pageNumber in pageNumbers"
              :key="pageNumber"
              type="button"
              class="pagination-number"
              :class="{ active: pageNumber === page }"
              :aria-current="pageNumber === page ? 'page' : undefined"
              @click="changePage(pageNumber)"
            >
              {{ pageNumber }}
            </button>
            <button
              v-if="hasTrailingEllipsis"
              type="button"
              class="pagination-jump"
              :aria-label="`마지막 페이지 ${totalPages}`"
              @click="changePage(totalPages)"
            >
              …
            </button>
          </div>
        </section>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronDown, Gamepad2, Search, Tag, ThumbsUp } from 'lucide-vue-next'
import { gamesApi } from '../api/games'
import GameImage from '../components/GameImage.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import AppLayout from '../layouts/AppLayout.vue'
import { money, percent } from '../utils/format'

const route = useRoute()
const router = useRouter()
const games = ref([])
const genres = ref([])
const loading = ref(false)
const activeTab = ref('deals')
const page = ref(Number(route.query.page || 1))
const pagination = ref({ count: 0, next: null, previous: null })
const allPriceValue = '80000'
const pageSize = 25
const pageWindowRadius = 2
const filters = reactive({
  q: route.query.q || '',
  genres: normalizeGenres(route.query.genre),
  max_price: route.query.max_price || allPriceValue,
  discount: route.query.discount || 0,
  discounted: route.query.discounted || '',
  include_dlc: route.query.include_dlc || '',
  ordering: route.query.ordering || '-steam_review_count',
  review_score: route.query.review_score || 0,
  review_count: route.query.review_count || 0,
})
const draft = reactive({ ...filters, genres: [...filters.genres] })
let filterApplyTimer = null
let lastSyncedDraftSignature = ''

const isPopularDealsView = computed(
  () =>
    route.path === '/games' &&
    route.query.ordering === '-steam_review_count' &&
    isDiscountedOnlyActive(route.query.discounted),
)

const pricePresets = [
  { label: '무료', value: '0' },
  { label: '10,000 이하', value: '10000' },
  { label: '20,000 이하', value: '20000' },
  { label: '40,000 이하', value: '40000' },
  { label: '모든 가격', value: allPriceValue },
]
const discountPresets = [
  { label: '-25%', value: '25' },
  { label: '-50%', value: '50' },
  { label: '-75%', value: '75' },
  { label: '-90%', value: '90' },
]
const reviewPresets = [
  { label: '복합적', value: '40' },
  { label: '대체로 긍정적', value: '70' },
  { label: '매우 긍정적', value: '80' },
  { label: '압도적으로 긍정적', value: '95' },
  { label: '전체 평가', value: '0' },
]

const totalPages = computed(() => Math.max(1, Math.ceil(Number(pagination.value.count || 0) / pageSize)))

const pageNumbers = computed(() => {
  const currentPage = Math.min(totalPages.value, Math.max(1, page.value))
  const firstPage = Math.max(1, currentPage - pageWindowRadius)
  const lastPage = Math.min(totalPages.value, currentPage + pageWindowRadius)
  return Array.from({ length: Math.max(0, lastPage - firstPage + 1) }, (_, index) => firstPage + index)
})

const hasLeadingEllipsis = computed(() => pageNumbers.value[0] > 1)

const hasTrailingEllipsis = computed(() => pageNumbers.value.at(-1) < totalPages.value)

const load = async () => {
  loading.value = true
  try {
    const response = await gamesApi.listPage({ ...requestParams(), page_size: pageSize, page: page.value })
    games.value = response.results?.data || []
    pagination.value = { count: response.count || games.value.length, next: response.next, previous: response.previous }
    if (pagination.value.count && page.value > totalPages.value) {
      changePage(totalPages.value)
    }
  } finally {
    loading.value = false
  }
}

const loadGenres = async () => {
  genres.value = await gamesApi.genres()
}

const requestParams = () => {
  if (isPopularDealsView.value) {
    return { ordering: '-steam_review_count', discounted: '1' }
  }

  return {
    ...(filters.q ? { q: filters.q } : {}),
    ...(filters.genres.length ? { genre: filters.genres } : {}),
    ...(isPriceFilterActive(filters.max_price) ? { max_price: filters.max_price } : {}),
    ...(isDiscountFilterActive(filters.discount) ? { discount: filters.discount } : {}),
    ...(isDiscountedOnlyActive(filters.discounted) ? { discounted: '1' } : {}),
    ...(isDlcIncluded(filters.include_dlc) ? { include_dlc: '1' } : {}),
    ...(isReviewScoreFilterActive(filters.review_score) ? { review_score: filters.review_score } : {}),
    ...(isReviewCountFilterActive(filters.review_count) ? { review_count: filters.review_count } : {}),
    ...(filters.ordering ? { ordering: filters.ordering } : {}),
  }
}

const buildQuery = (nextPage = 1) => ({
  ...requestParams(),
  ...(nextPage > 1 ? { page: nextPage } : {}),
})

const applyFilters = () => {
  page.value = 1
  Object.assign(draft, { ...filters, genres: [...filters.genres] })
  lastSyncedDraftSignature = draftFilterSignature()
  router.push({ path: '/games', query: buildQuery(1) })
}

const toggleFilterSection = (section) => {
  activeTab.value = activeTab.value === section ? '' : section
}


const draftFilterSignature = () =>
  JSON.stringify({
    genres: [...draft.genres].sort(),
    max_price: String(draft.max_price || allPriceValue),
    discount: String(draft.discount || 0),
    include_dlc: isDlcIncluded(draft.include_dlc) ? '1' : '0',
    review_score: String(draft.review_score || 0),
    review_count: String(draft.review_count || 0),
  })

const scheduleRealtimeFilters = () => {
  const signature = draftFilterSignature()
  if (signature === lastSyncedDraftSignature) return
  window.clearTimeout(filterApplyTimer)
  filterApplyTimer = window.setTimeout(() => {
    filters.genres = [...draft.genres]
    filters.max_price = draft.max_price
    filters.discount = draft.discount
    filters.include_dlc = draft.include_dlc
    filters.review_score = draft.review_score
    filters.review_count = draft.review_count
    page.value = 1
    lastSyncedDraftSignature = draftFilterSignature()
    router.replace({ path: '/games', query: buildQuery(1) })
  }, 160)
}

const changePage = (nextPage) => {
  page.value = Math.min(totalPages.value, Math.max(1, nextPage))
  router.push({ path: '/games', query: buildQuery(page.value) })
}

const syncFromRoute = () => {
  filters.q = route.query.q || ''
  filters.genres = normalizeGenres(route.query.genre)
  filters.max_price = route.query.max_price || allPriceValue
  filters.discount = route.query.discount || 0
  filters.discounted = route.query.discounted || ''
  filters.include_dlc = route.query.include_dlc || ''
  filters.ordering = route.query.ordering || '-steam_review_count'
  filters.review_score = route.query.review_score || 0
  filters.review_count = route.query.review_count || 0
  page.value = Number(route.query.page || 1)
  Object.assign(draft, { ...filters, genres: [...filters.genres] })
  lastSyncedDraftSignature = draftFilterSignature()
}

const genreText = (game) => game.genres?.map((genre) => genre.name).filter(Boolean).join(', ') || '장르 정보 없음'

const isDiscounted = (game) => Number(game.max_discount || 0) > 0 && Number(game.original_price || 0) > Number(game.best_price || 0)

const priceLabel = (value) => {
  const price = Number(value || 0)
  if (String(value) === allPriceValue) return '모든 가격'
  if (!price) return '무료'
  return `${price.toLocaleString('ko-KR')} 이하`
}

const isPriceFilterActive = (value) => String(value) !== allPriceValue

const isDiscountFilterActive = (value) => Number(value || 0) > 0

const isDiscountedOnlyActive = (value) => ['1', 'true'].includes(String(value || '').toLowerCase())

const isDlcIncluded = (value) => ['1', 'true'].includes(String(value || '').toLowerCase())

const toggleDlcDisplay = () => {
  draft.include_dlc = isDlcIncluded(draft.include_dlc) ? '' : '1'
}

const isReviewScoreFilterActive = (value) => Number(value || 0) > 0

const isReviewCountFilterActive = (value) => Number(value || 0) > 0

const reviewScoreSteps = [0, 40, 70, 80, 95]

const reviewScoreToSlider = (value) => {
  const score = Number(value || 0)
  if (score >= 95) return 4
  if (score >= 80) return 3
  if (score >= 70) return 2
  if (score >= 40) return 1
  return 0
}

const reviewSliderToScore = (value) => reviewScoreSteps[Number(value)] || 0

const reviewScoreLabel = (value) => {
  const score = Number(value || 0)
  if (score >= 95) return '압도적으로 긍정적'
  if (score >= 80) return '매우 긍정적 이상'
  if (score >= 70) return '대체로 긍정적 이상'
  if (score >= 40) return '복합적 이상'
  return '전체 평가'
}

const reviewCountLabel = (value) => {
  const count = Number(value || 0)
  if (!count) return '전체 리뷰 수'
  return `${count.toLocaleString('ko-KR')}개 이상`
}

const goToGame = (id) => router.push(`/games/${id}`)

function normalizeGenres(value) {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}

watch(
  () => route.query,
  () => {
    syncFromRoute()
    load()
  },
)

watch(
  () => [
    draft.max_price,
    draft.discount,
    draft.include_dlc,
    draft.review_score,
    draft.review_count,
    draft.genres.join('|'),
  ],
  scheduleRealtimeFilters,
)

onMounted(async () => {
  await loadGenres()
  await load()
})
</script>
