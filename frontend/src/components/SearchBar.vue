<template>
  <div class="search-box">
    <form class="search-bar" @submit.prevent="submit">
      <input
        v-model="query"
        type="search"
        :placeholder="labels.placeholder"
        autocomplete="off"
        @focus="isFocused = true"
        @blur="handleBlur"
        @keydown.down.prevent="moveSelection(1)"
        @keydown.up.prevent="moveSelection(-1)"
        @keydown.enter="chooseHighlighted"
        @keydown.esc="closeSuggestions"
      />
      <button type="submit" :aria-label="labels.search">
        <Search :size="18" />
      </button>
    </form>

    <div v-if="showSuggestions" class="search-suggestions" @mousedown.prevent>
      <div class="suggestion-heading">{{ labels.results }}</div>
      <button
        v-for="(game, index) in suggestions"
        :key="game.id"
        type="button"
        class="suggestion-row"
        :class="{ selected: index === highlightedIndex }"
        @mouseenter="highlightedIndex = index"
        @click="goToGame(game)"
      >
        <GameImage
          :src="game.thumbnail || game.hero_image"
          :alt="game.title"
          :steam-app-id="game.steam_app_id"
          fallback-class="suggestion-fallback"
        />
        <span class="suggestion-copy">
          <strong>{{ game.title }}</strong>
          <small>{{ game.platform || 'Steam' }}</small>
        </span>
        <span class="suggestion-price" :class="{ discounted: isDiscounted(game) }">
          <strong>{{ money(game.best_price) }}</strong>
          <small v-if="isDiscounted(game)">{{ percent(game.max_discount) }} {{ labels.discount }}</small>
        </span>
      </button>
      <div v-if="isLoading" class="suggestion-state">{{ labels.loading }}</div>
      <div v-else-if="!suggestions.length" class="suggestion-state">{{ labels.empty }}</div>
      <button type="button" class="search-filter-button" @click="openSearchFilters">
        {{ labels.filter }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from 'lucide-vue-next'
import { gamesApi } from '../api/games'
import { money, percent } from '../utils/format'
import GameImage from './GameImage.vue'

const labels = {
  placeholder: '\uac8c\uc784, \uc7a5\ub974, \ud0dc\uadf8\ub97c \uac80\uc0c9\ud574\ubcf4\uc138\uc694',
  search: '\uac80\uc0c9',
  results: '\uac80\uc0c9 \uacb0\uacfc',
  discount: '\ud560\uc778',
  loading: '\uac80\uc0c9 \uc911...',
  empty: '\uc5f0\uad00 \uac80\uc0c9\uc5b4\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.',
  filter: '\uac80\uc0c9 \ud544\ud130',
}

const query = ref('')
const router = useRouter()
const suggestions = ref([])
const isFocused = ref(false)
const isLoading = ref(false)
const highlightedIndex = ref(-1)
let searchTimer = null
let requestId = 0
const suggestionCache = new Map()

const trimmedQuery = computed(() => query.value.trim())
const showSuggestions = computed(() => isFocused.value && trimmedQuery.value.length >= 2)

const fetchSuggestions = async (term) => {
  const cacheKey = term.toLowerCase()
  if (suggestionCache.has(cacheKey)) {
    suggestions.value = suggestionCache.get(cacheKey)
    highlightedIndex.value = suggestions.value.length ? 0 : -1
    return
  }

  const currentRequest = ++requestId
  isLoading.value = true
  try {
    const results = await gamesApi.suggest(term)
    if (currentRequest !== requestId) return
    suggestions.value = results.slice(0, 6)
    suggestionCache.set(cacheKey, suggestions.value)
    highlightedIndex.value = suggestions.value.length ? 0 : -1
  } catch {
    if (currentRequest !== requestId) return
    suggestions.value = []
    highlightedIndex.value = -1
  } finally {
    if (currentRequest === requestId) isLoading.value = false
  }
}

watch(trimmedQuery, (term) => {
  window.clearTimeout(searchTimer)
  requestId += 1
  suggestions.value = []
  highlightedIndex.value = -1

  if (term.length < 2) {
    isLoading.value = false
    return
  }

  searchTimer = window.setTimeout(() => fetchSuggestions(term), 250)
})

onBeforeUnmount(() => window.clearTimeout(searchTimer))

const submit = () => {
  closeSuggestions()
  router.push({ path: '/games', query: trimmedQuery.value ? { q: trimmedQuery.value, include_dlc: '1' } : {} })
}

const goToGame = (game) => {
  closeSuggestions()
  router.push(`/games/${game.id}`)
}

const isDiscounted = (game) => Number(game?.max_discount || 0) > 0

const openSearchFilters = () => {
  closeSuggestions()
  router.push({ path: '/games', query: trimmedQuery.value ? { q: trimmedQuery.value, include_dlc: '1' } : {} })
}

const moveSelection = (step) => {
  if (!suggestions.value.length) return
  const nextIndex = highlightedIndex.value + step
  highlightedIndex.value = (nextIndex + suggestions.value.length) % suggestions.value.length
}

const chooseHighlighted = (event) => {
  if (highlightedIndex.value < 0 || !suggestions.value[highlightedIndex.value]) return
  event.preventDefault()
  goToGame(suggestions.value[highlightedIndex.value])
}

const closeSuggestions = () => {
  isFocused.value = false
}

const handleBlur = () => {
  window.setTimeout(closeSuggestions, 120)
}
</script>
