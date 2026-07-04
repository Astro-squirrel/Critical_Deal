<template>
  <AppLayout>
    <div class="wishlist-page">
      <section class="panel list-header wishlist-header">
        <h1>위시리스트</h1>
      </section>

      <LoadingSpinner v-if="loading" />
      <p v-else-if="!items.length" class="profile-empty">아직 위시리스트에 담은 게임이 없습니다.</p>
      <div v-else class="cards-grid">
        <div v-for="item in items" :key="item.game.id" class="wishlist-card-wrap">
          <GameCard :game="item.game" />
          <button
            class="wishlist-remove-button"
            :class="{ removed: isLocallyRemoved(item) }"
            type="button"
            :data-tooltip="heartLabel(item)"
            :aria-label="heartLabel(item)"
            :disabled="pendingGameId === gameIdOf(item)"
            @click.stop="toggleItem(item)"
          >
            <Heart
              aria-hidden="true"
              :size="24"
              :stroke-width="2.2"
              :fill="isLocallyRemoved(item) ? 'none' : 'currentColor'"
            />
          </button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Heart } from 'lucide-vue-next'
import { wishlistApi } from '../api/wishlist'
import AppLayout from '../layouts/AppLayout.vue'
import GameCard from '../components/GameCard.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const items = ref([])
const loading = ref(true)
const pendingGameId = ref(null)
const removedGameIds = ref(new Set())

const loadItems = async () => {
  loading.value = true
  try {
    items.value = await wishlistApi.list()
    removedGameIds.value = new Set()
  } finally {
    loading.value = false
  }
}

const gameIdOf = (item) => Number(item.game?.id)

const isLocallyRemoved = (item) => removedGameIds.value.has(gameIdOf(item))

const heartLabel = (item) => (isLocallyRemoved(item) ? '위시리스트 추가' : '위시리스트 삭제')

const setLocallyRemoved = (gameId, removed) => {
  const next = new Set(removedGameIds.value)
  if (removed) {
    next.add(gameId)
  } else {
    next.delete(gameId)
  }
  removedGameIds.value = next
}

const toggleItem = async (item) => {
  const gameId = gameIdOf(item)
  if (!gameId || pendingGameId.value === gameId) return
  pendingGameId.value = gameId
  try {
    if (isLocallyRemoved(item)) {
      const addedItem = await wishlistApi.add(gameId)
      if (addedItem?.id) item.id = addedItem.id
      setLocallyRemoved(gameId, false)
    } else {
      await wishlistApi.remove(item.id)
      setLocallyRemoved(gameId, true)
    }
  } finally {
    pendingGameId.value = null
  }
}

onMounted(loadItems)
</script>
