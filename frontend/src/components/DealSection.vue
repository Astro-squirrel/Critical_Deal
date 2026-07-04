<template>
  <section class="panel">
    <div class="section-title">
      <div>
        <span class="section-eyebrow">Best deals</span>
        <h2>{{ title }}</h2>
      </div>
      <router-link to="/games">더 보기</router-link>
    </div>
    <div class="deal-list">
      <GameCard v-for="game in games" :key="game.id" :game="game" />
      <p v-if="!games.length" class="empty-preview">할인 게임 정보를 불러오는 중입니다.</p>
    </div>
  </section>
</template>

<script setup>
import GameCard from './GameCard.vue'

defineProps({
  title: { type: String, required: true },
  games: { type: Array, default: () => [] },
})
</script>
