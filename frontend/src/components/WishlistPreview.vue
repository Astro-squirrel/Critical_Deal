<template>
  <section class="panel side-panel">
    <div class="section-title">
      <div>
        <span class="section-eyebrow">Watchlist</span>
        <h2>위시리스트</h2>
      </div>
      <router-link to="/wishlist">전체 보기</router-link>
    </div>
    <p v-if="!items.length" class="empty-preview">아직 위시리스트에 담은 게임이 없습니다.</p>
    <template v-for="item in items" :key="item.id || item.title">
      <router-link v-if="gameId(item)" class="wish-row" :to="`/games/${gameId(item)}`">
        <img :src="item.game?.thumbnail || item.thumbnail" :alt="item.game?.title || item.title" />
        <span>{{ item.game?.title || item.title }}</span>
        <strong>{{ money(item.game?.best_price || item.best_price) }}</strong>
      </router-link>
      <div v-else class="wish-row">
        <img :src="item.game?.thumbnail || item.thumbnail" :alt="item.game?.title || item.title" />
        <span>{{ item.game?.title || item.title }}</span>
        <strong>{{ money(item.game?.best_price || item.best_price) }}</strong>
      </div>
    </template>
  </section>
</template>

<script setup>
import { money } from '../utils/format'

defineProps({ items: { type: Array, default: () => [] } })

const gameId = (item) => item.game?.id || item.game_id || null
</script>
