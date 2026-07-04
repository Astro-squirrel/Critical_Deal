<template>
  <article
    class="game-card"
    role="button"
    tabindex="0"
    @click="$router.push(`/games/${game.id}`)"
    @keydown.enter.prevent="$router.push(`/games/${game.id}`)"
    @keydown.space.prevent="$router.push(`/games/${game.id}`)"
  >
    <GameImage :src="game.thumbnail || game.hero_image" :alt="game.title" :steam-app-id="game.steam_app_id" />
    <div class="game-card-copy">
      <h3>{{ game.title }}</h3>
      <p>{{ genreText }}</p>
    </div>
    <div class="card-meta">
      <span v-if="game.max_discount" class="discount">-{{ game.max_discount }}%</span>
      <span class="price-stack">
        <del v-if="isDiscounted">{{ money(game.original_price) }}</del>
        <strong>{{ money(game.best_price) }}</strong>
      </span>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue'
import { money } from '../utils/format'
import GameImage from './GameImage.vue'

const props = defineProps({ game: { type: Object, required: true } })
const genreText = computed(() => props.game.genres?.map((g) => g.name).join(', ') || props.game.platform || 'Steam')
const isDiscounted = computed(
  () => Number(props.game.max_discount || 0) > 0 && Number(props.game.original_price || 0) > Number(props.game.best_price || 0),
)
</script>
