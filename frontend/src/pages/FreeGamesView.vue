<template>
  <AppLayout>
    <section class="list-header panel free-games-header">
      <div>
        <h1>지금 무료로 받기</h1>
        <p>Steam과 Epic Games에서 현재 무료로 받을 수 있는 게임입니다.</p>
      </div>
      <div class="segmented-control">
        <button type="button" :class="{ active: selectedSource === 'all' }" @click="selectedSource = 'all'">전체</button>
        <button type="button" :class="{ active: selectedSource === 'Steam' }" @click="selectedSource = 'Steam'">Steam</button>
        <button type="button" :class="{ active: selectedSource === 'Epic Games' }" @click="selectedSource = 'Epic Games'">Epic Games</button>
      </div>
    </section>

    <LoadingSpinner v-if="loading" />
    <section v-else class="panel free-games-panel">
      <div class="free-games-list">
        <article v-for="game in filteredGames" :key="game.id || `${game.source}-${game.title}`" class="free-game-row">
          <img v-if="game.thumbnail" :src="game.thumbnail" :alt="game.title" />
          <div v-else class="free-image-fallback">{{ game.title?.slice(0, 2) }}</div>
          <div class="free-game-copy">
            <strong>{{ game.title }}</strong>
            <span>{{ game.source }}</span>
            <small>{{ game.ends_at ? `${formatDate(game.ends_at)}까지` : '기간 정보 없음' }}</small>
          </div>
          <a :href="game.claim_url" target="_blank" rel="noreferrer">받으러 가기</a>
        </article>
        <p v-if="!filteredGames.length" class="profile-empty">현재 조건에 맞는 무료 배포 게임이 없습니다.</p>
      </div>
    </section>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { gamesApi } from '../api/games'
import AppLayout from '../layouts/AppLayout.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const games = ref([])
const loading = ref(true)
const selectedSource = ref('all')

const filteredGames = computed(() => {
  if (selectedSource.value === 'all') return games.value
  return games.value.filter((game) => game.source === selectedSource.value)
})

const formatDate = (value) =>
  new Intl.DateTimeFormat('ko-KR', { month: 'long', day: 'numeric' }).format(new Date(value))

onMounted(async () => {
  try {
    games.value = await gamesApi.epicFree()
  } finally {
    loading.value = false
  }
})
</script>
